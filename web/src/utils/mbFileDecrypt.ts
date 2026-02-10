import { buildFileChunkAad, decryptWithKey } from '@/utils/crypto'

export type MbFileManifest = {
  version: number
  paste_id: string
  file_id: string
  encryption_mode: string
  plain_size: number
  chunk_size: number
  total_chunks: number
  chunk_overhead_bytes: number
  chunk_format: string
  aad_format: string
  aad_prefix?: string | null
  aad_required: boolean
  iv_scheme: string
  iv_prefix?: string | null
}

function concatBytes(a: Uint8Array, b: Uint8Array): Uint8Array {
  if (a.byteLength === 0) return b
  if (b.byteLength === 0) return a
  const out = new Uint8Array(a.byteLength + b.byteLength)
  out.set(a, 0)
  out.set(b, a.byteLength)
  return out
}

async function readExactly(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  state: { buf: Uint8Array },
  n: number,
  signal?: AbortSignal,
  onReadBytes?: (n: number) => void
): Promise<Uint8Array> {
  if (!Number.isInteger(n) || n < 0) throw new Error(`readExactly: n无效: ${n}`)

  while (state.buf.byteLength < n) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    const { done, value } = await reader.read()
    if (done) break
    if (value && value.byteLength > 0) {
      onReadBytes?.(value.byteLength)
      state.buf = concatBytes(state.buf, value)
    }
  }

  if (state.buf.byteLength < n) {
    throw new Error(`读取文件流失败：期望${n}字节，但仅收到${state.buf.byteLength}字节`)
  }

  const out = state.buf.slice(0, n)
  state.buf = state.buf.slice(n)
  return out
}

export async function* decryptChunkedFileStream(
  encryptedStream: ReadableStream<Uint8Array>,
  manifest: Pick<
    MbFileManifest,
    'plain_size' | 'chunk_size' | 'total_chunks' | 'chunk_overhead_bytes' | 'aad_required'
  >,
  key: Uint8Array,
  ids: { pasteId: string; fileId: string },
  opts?: {
    signal?: AbortSignal
    /**
     * Plain bytes progress (based on decrypted chunks; updates once per chunk).
     */
    onProgress?: (plainBytesDone: number, plainBytesTotal: number) => void
    /**
     * Plain bytes progress mapped from encrypted stream reads (smooth / real-time).
     * This is meant for "download progress" UI, even though actual decryption
     * still happens per chunk.
     */
    onPlainDownloadProgress?: (plainBytesDone: number, plainBytesTotal: number) => void
    onEncryptedProgress?: (encryptedBytesDone: number, encryptedBytesTotal: number) => void
  }
): AsyncGenerator<Uint8Array> {
  const plainSize = Number(manifest.plain_size)
  const chunkSize = Number(manifest.chunk_size)
  const totalChunks = Number(manifest.total_chunks)
  const overhead = Number(manifest.chunk_overhead_bytes)
  const aadRequired = Boolean(manifest.aad_required)

  if (!Number.isFinite(plainSize) || plainSize < 0) throw new Error('manifest.plain_size无效')
  if (!Number.isFinite(chunkSize) || chunkSize <= 0) throw new Error('manifest.chunk_size无效')
  if (!Number.isFinite(totalChunks) || totalChunks <= 0) throw new Error('manifest.total_chunks无效')
  if (overhead !== 28) throw new Error(`不支持的chunk_overhead_bytes: ${overhead}（期望28）`)

  // AES-GCM format: IV(12B) + ciphertext(plainLen) + tag(16B)
  const AES_GCM_IV_BYTES = 12

  const reader = encryptedStream.getReader()
  const state = { buf: new Uint8Array(0) }
  let plainDone = 0
  let encryptedDone = 0
  const encryptedTotal = plainSize + totalChunks * overhead

  // Smooth "downloaded plain bytes" estimate derived from encrypted bytes read.
  // This maps IV/tag overhead away so the UI can show `plainDone / plainTotal`
  // progress without waiting for an entire chunk to decrypt.
  let plainDownloaded = 0
  let progChunkIndex = 0
  let progEncOffsetInChunk = 0

  function expectedPlainSizeForChunk(chunkIndex: number): number {
    if (chunkIndex < totalChunks - 1) return chunkSize
    const v = plainSize - chunkSize * (totalChunks - 1)
    if (!Number.isFinite(v) || v <= 0) return 0
    return v
  }

  function clampPlainContribution(encOffset: number, expectedPlain: number): number {
    if (expectedPlain <= 0) return 0
    if (!Number.isFinite(encOffset) || encOffset <= 0) return 0
    // Exclude IV bytes. Tag bytes come after ciphertext so they don't add to this.
    const v = encOffset - AES_GCM_IV_BYTES
    if (v <= 0) return 0
    return v >= expectedPlain ? expectedPlain : v
  }

  function applyEncryptedDeltaToPlainDownloaded(deltaEncryptedBytes: number) {
    let remaining = deltaEncryptedBytes
    while (remaining > 0 && progChunkIndex < totalChunks) {
      const expectedPlain = expectedPlainSizeForChunk(progChunkIndex)
      const encryptedLen = expectedPlain + overhead

      const take = Math.min(remaining, encryptedLen - progEncOffsetInChunk)
      const before = progEncOffsetInChunk
      const after = before + take

      const plainBefore = clampPlainContribution(before, expectedPlain)
      const plainAfter = clampPlainContribution(after, expectedPlain)
      plainDownloaded += plainAfter - plainBefore

      progEncOffsetInChunk = after
      remaining -= take

      if (progEncOffsetInChunk >= encryptedLen) {
        progChunkIndex += 1
        progEncOffsetInChunk = 0
      }
    }

    if (plainDownloaded > plainSize) plainDownloaded = plainSize
  }

  try {
    for (let i = 0; i < totalChunks; i++) {
      if (opts?.signal?.aborted) throw new DOMException('Aborted', 'AbortError')

      let expectedPlain =
        i < totalChunks - 1 ? chunkSize : plainSize - chunkSize * (totalChunks - 1)
      if (!Number.isFinite(expectedPlain) || expectedPlain < 0) expectedPlain = 0

      const encryptedLen = expectedPlain + overhead
      const encryptedChunk = await readExactly(reader, state, encryptedLen, opts?.signal, (n) => {
        encryptedDone += n
        opts?.onEncryptedProgress?.(encryptedDone, encryptedTotal)

        if (opts?.onPlainDownloadProgress) {
          applyEncryptedDeltaToPlainDownloaded(n)
          opts.onPlainDownloadProgress(plainDownloaded, plainSize)
        }
      })

      const aad = aadRequired ? buildFileChunkAad(ids.pasteId, ids.fileId, i, totalChunks) : undefined
      const plain = await decryptWithKey(encryptedChunk, key, aad ? { aad } : undefined)

      plainDone += plain.byteLength
      opts?.onProgress?.(plainDone, plainSize)

      yield plain
    }
  } finally {
    try {
      await reader.cancel()
    } catch {
      // ignore
    }
  }
}

export async function decryptChunkedFileToBlob(
  encryptedStream: ReadableStream<Uint8Array>,
  manifest: Pick<
    MbFileManifest,
    'plain_size' | 'chunk_size' | 'total_chunks' | 'chunk_overhead_bytes' | 'aad_required'
  >,
  key: Uint8Array,
  ids: { pasteId: string; fileId: string },
  mimeType: string,
  opts?: {
    signal?: AbortSignal
    /**
     * Plain bytes progress (based on decrypted chunks; updates once per chunk).
     */
    onProgress?: (plainBytesDone: number, plainBytesTotal: number) => void
    /**
     * Plain bytes progress mapped from encrypted stream reads (smooth / real-time).
     */
    onPlainDownloadProgress?: (plainBytesDone: number, plainBytesTotal: number) => void
    onEncryptedProgress?: (encryptedBytesDone: number, encryptedBytesTotal: number) => void
  }
): Promise<Blob> {
  const parts: BlobPart[] = []
  for await (const chunk of decryptChunkedFileStream(encryptedStream, manifest, key, ids, opts)) {
    parts.push(chunk as unknown as BlobPart)
  }
  return new Blob(parts, { type: mimeType || 'application/octet-stream' })
}

export async function decryptWholeFileToBlob(
  encryptedBytes: Uint8Array,
  key: Uint8Array,
  mimeType: string
): Promise<Blob> {
  const plain = await decryptWithKey(encryptedBytes, key)
  return new Blob([plain as unknown as BlobPart], { type: mimeType || 'application/octet-stream' })
}
