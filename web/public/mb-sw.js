/* MaterialBin decrypting Service Worker
 *
 * Purpose:
 * - Provide a "plaintext view" for encrypted files via a virtual URL:
 *     /mb/plain/pastes/{paste_id}/files/{file_id}
 * - Support HTTP Range on the *plaintext* stream, enabling video seeking.
 *
 * The SW never sends the encryption key to the backend. The page must provide
 * the key via postMessage({ type: 'mb:set-context', pasteId, encryptionKeyBytes, accessKey, adminKey }).
 */

'use strict'

const MB_PLAIN_PATH_RE = /^\/mb\/plain\/pastes\/([A-Za-z0-9_-]+)\/files\/([0-9a-fA-F-]{36})$/

const MANIFEST_TTL_MS = 5 * 60 * 1000
const META_TTL_MS = 5 * 60 * 1000

// pasteId -> { keyBytes: Uint8Array, cryptoKey: CryptoKey, accessKey: string|null, adminKey: string|null }
const pasteContexts = new Map()

// `${pasteId}:${fileId}` -> { manifest, ts }
const manifestCache = new Map()

// `${pasteId}:${fileId}` -> { mimeType, ts }
const metaCache = new Map()

const textEncoder = new TextEncoder()

function buildAad(pasteId, fileId, chunkIndex, totalChunks) {
  const aadStr = `mb:filechunk:v1|paste:${pasteId}|file:${fileId}|i:${chunkIndex}|n:${totalChunks}`
  return textEncoder.encode(aadStr)
}

function toUint8Key(value) {
  if (!value) return null
  if (value instanceof Uint8Array) return value
  if (Array.isArray(value)) return new Uint8Array(value)
  if (value instanceof ArrayBuffer) return new Uint8Array(value)
  return null
}

function buildAccessKeyQuery(accessKey) {
  if (!accessKey) return ''
  const trimmed = String(accessKey).trim()
  if (!trimmed) return ''
  return `?access_key=${encodeURIComponent(trimmed)}`
}

function buildAdminAuthHeader(adminKey) {
  if (!adminKey) return null
  const trimmed = String(adminKey).trim()
  if (!trimmed) return null
  return `Bearer ${trimmed}`
}

function manifestCacheKey(pasteId, fileId) {
  return `${pasteId}:${fileId}`
}

async function fetchJson(url, authHeaderOrNull) {
  const headers = new Headers()
  if (authHeaderOrNull) headers.set('Authorization', authHeaderOrNull)

  const resp = await fetch(url, { cache: 'no-store', headers })
  if (!resp.ok) {
    const err = new Error(`HTTP ${resp.status}`)
    err.status = resp.status
    err.response = resp
    throw err
  }
  return await resp.json()
}

async function getManifest(pasteId, fileId, accessKey, adminKey) {
  const key = manifestCacheKey(pasteId, fileId)
  const cached = manifestCache.get(key)
  if (cached && Date.now() - cached.ts < MANIFEST_TTL_MS) return cached.manifest

  const url =
    `/api/pastes/${encodeURIComponent(pasteId)}/files/${encodeURIComponent(fileId)}/manifest` +
    buildAccessKeyQuery(accessKey)
  const manifest = await fetchJson(url, buildAdminAuthHeader(adminKey))
  manifestCache.set(key, { manifest, ts: Date.now() })
  return manifest
}

async function getMimeType(pasteId, fileId, accessKey, adminKey) {
  const key = manifestCacheKey(pasteId, fileId)
  const cached = metaCache.get(key)
  if (cached && Date.now() - cached.ts < META_TTL_MS) return cached.mimeType

  const url =
    `/api/pastes/${encodeURIComponent(pasteId)}/files/${encodeURIComponent(fileId)}/meta` +
    buildAccessKeyQuery(accessKey)
  const meta = await fetchJson(url, buildAdminAuthHeader(adminKey))
  const mimeType = (meta && meta.mime_type) ? String(meta.mime_type) : 'application/octet-stream'
  metaCache.set(key, { mimeType, ts: Date.now() })
  return mimeType
}

function parseRangeHeader(rangeHeader, size) {
  if (!rangeHeader) return null
  const raw = String(rangeHeader).trim()
  if (!raw.startsWith('bytes=')) return null

  const spec = raw.slice('bytes='.length).trim()
  if (!spec) return null
  if (spec.includes(',')) {
    // Multiple ranges are not supported.
    return { error: 416 }
  }

  const [a, b] = spec.split('-', 2)
  const startStr = (a || '').trim()
  const endStr = (b || '').trim()

  let start = null
  let end = null

  if (startStr === '') {
    // suffix: "-N" (last N bytes)
    const suffixLen = Number.parseInt(endStr, 10)
    if (!Number.isFinite(suffixLen) || suffixLen <= 0) return { error: 416 }
    const clamped = Math.min(suffixLen, size)
    start = Math.max(0, size - clamped)
    end = size - 1
  } else {
    start = Number.parseInt(startStr, 10)
    if (!Number.isFinite(start) || start < 0) return { error: 416 }
    if (endStr === '') {
      end = size - 1
    } else {
      end = Number.parseInt(endStr, 10)
      if (!Number.isFinite(end) || end < 0) return { error: 416 }
    }
  }

  if (start === null || end === null) return { error: 416 }
  if (size <= 0) return { error: 416 }
  if (start >= size) return { error: 416 }

  start = Math.max(0, start)
  end = Math.min(size - 1, end)
  if (start > end) return { error: 416 }

  return { start, end }
}

async function readExactly(reader, state, n) {
  if (!Number.isInteger(n) || n < 0) throw new Error(`readExactly: invalid n=${n}`)

  while (state.buf.byteLength < n) {
    const { done, value } = await reader.read()
    if (done) break
    if (value && value.byteLength > 0) {
      const merged = new Uint8Array(state.buf.byteLength + value.byteLength)
      merged.set(state.buf, 0)
      merged.set(value, state.buf.byteLength)
      state.buf = merged
    }
  }

  if (state.buf.byteLength < n) {
    throw new Error(`Upstream stream ended early: need=${n}, got=${state.buf.byteLength}`)
  }

  const out = state.buf.slice(0, n)
  state.buf = state.buf.slice(n)
  return out
}

async function decryptChunk(encryptedChunk, cryptoKey, aadBytesOrNull) {
  if (!encryptedChunk || encryptedChunk.byteLength < 12 + 16) {
    throw new Error('Invalid encrypted chunk length')
  }
  const iv = encryptedChunk.slice(0, 12)
  const ciphertext = encryptedChunk.slice(12)

  const algo = { name: 'AES-GCM', iv }
  if (aadBytesOrNull) algo.additionalData = aadBytesOrNull

  const plainBuf = await crypto.subtle.decrypt(algo, cryptoKey, ciphertext)
  return new Uint8Array(plainBuf)
}

async function handlePlainFileRequest(request, pasteId, fileId) {
  const ctx = pasteContexts.get(pasteId)
  if (!ctx || !ctx.cryptoKey) {
    return new Response('Missing decryption context for this paste.', { status: 412 })
  }

  let manifest
  try {
    manifest = await getManifest(pasteId, fileId, ctx.accessKey, ctx.adminKey)
  } catch (e) {
    const status = Number(e && e.status) || 500
    return new Response(`Failed to fetch manifest: HTTP ${status}`, { status })
  }

  const plainSize = Number(manifest && manifest.plain_size)
  const chunkSize = Number(manifest && manifest.chunk_size)
  const totalChunks = Number(manifest && manifest.total_chunks)
  const overhead = Number(manifest && manifest.chunk_overhead_bytes)
  const aadRequired = Boolean(manifest && manifest.aad_required)

  if (!Number.isFinite(plainSize) || plainSize < 0) return new Response('Bad manifest.plain_size', { status: 500 })
  if (!Number.isFinite(chunkSize) || chunkSize <= 0) return new Response('Bad manifest.chunk_size', { status: 500 })
  if (!Number.isFinite(totalChunks) || totalChunks <= 0) return new Response('Bad manifest.total_chunks', { status: 500 })
  if (overhead !== 28) return new Response('Unsupported chunk_overhead_bytes', { status: 500 })

  const rangeParsed = parseRangeHeader(request.headers.get('Range'), plainSize)
  if (rangeParsed && rangeParsed.error) {
    return new Response('Requested Range Not Satisfiable', {
      status: 416,
      headers: { 'Content-Range': `bytes */${plainSize}` }
    })
  }

  const start = rangeParsed ? rangeParsed.start : 0
  const end = rangeParsed ? rangeParsed.end : Math.max(0, plainSize - 1)
  const isRange = !!rangeParsed

  // HEAD: no body.
  if (request.method === 'HEAD') {
    let mimeType = 'application/octet-stream'
    try {
      mimeType = await getMimeType(pasteId, fileId, ctx.accessKey, ctx.adminKey)
    } catch {
      // ignore
    }

    const headers = new Headers()
    headers.set('Content-Type', mimeType)
    headers.set('Accept-Ranges', 'bytes')
    if (isRange) {
      headers.set('Content-Range', `bytes ${start}-${end}/${plainSize}`)
      headers.set('Content-Length', String(end - start + 1))
      return new Response(null, { status: 206, headers })
    }
    headers.set('Content-Length', String(plainSize))
    return new Response(null, { status: 200, headers })
  }

  const stride = chunkSize + overhead
  const startChunk = Math.floor(start / chunkSize)
  const endChunk = Math.floor(end / chunkSize)
  const startInChunk = start - startChunk * chunkSize
  const endInChunk = end - endChunk * chunkSize

  function expectedPlainSize(chunkIndex) {
    if (chunkIndex < totalChunks - 1) return chunkSize
    const last = plainSize - chunkSize * (totalChunks - 1)
    return Math.max(0, Number.isFinite(last) ? last : 0)
  }

  const encStart = startChunk * stride
  const encEnd = (endChunk * stride) + (expectedPlainSize(endChunk) + overhead) - 1

  const fileUrl =
    `/api/pastes/${encodeURIComponent(pasteId)}/files/${encodeURIComponent(fileId)}` +
    buildAccessKeyQuery(ctx.accessKey)

  const abortController = new AbortController()
  const authHeader = buildAdminAuthHeader(ctx.adminKey)
  const upstreamHeaders = new Headers()
  upstreamHeaders.set('Range', `bytes=${encStart}-${encEnd}`)
  if (authHeader) upstreamHeaders.set('Authorization', authHeader)
  const upstreamResp = await fetch(fileUrl, {
    headers: upstreamHeaders,
    cache: 'no-store',
    signal: abortController.signal
  })

  if (!upstreamResp.ok || !upstreamResp.body) {
    const status = upstreamResp.status || 500
    return new Response(`Failed to fetch encrypted data: HTTP ${status}`, { status })
  }

  const mimeType = upstreamResp.headers.get('Content-Type') || 'application/octet-stream'

  const headers = new Headers()
  headers.set('Content-Type', mimeType)
  headers.set('Accept-Ranges', 'bytes')
  if (isRange) {
    headers.set('Content-Range', `bytes ${start}-${end}/${plainSize}`)
    headers.set('Content-Length', String(end - start + 1))
  } else {
    headers.set('Content-Length', String(plainSize))
  }

  const cryptoKey = ctx.cryptoKey
  const reader = upstreamResp.body.getReader()
  const state = { buf: new Uint8Array(0) }

  const stream = new ReadableStream({
    async start(controller) {
      try {
        for (let idx = startChunk; idx <= endChunk; idx++) {
          const expectedPlain = expectedPlainSize(idx)
          const encryptedLen = expectedPlain + overhead

          const encryptedChunk = await readExactly(reader, state, encryptedLen)
          const aad = aadRequired ? buildAad(pasteId, fileId, idx, totalChunks) : null
          const plain = await decryptChunk(encryptedChunk, cryptoKey, aad)

          const sliceStart = idx === startChunk ? startInChunk : 0
          const sliceEndExclusive = idx === endChunk ? (endInChunk + 1) : plain.byteLength

          if (sliceStart < 0 || sliceEndExclusive < sliceStart) {
            throw new Error('Invalid slice range')
          }

          const out = plain.slice(sliceStart, sliceEndExclusive)
          if (out.byteLength > 0) controller.enqueue(out)
        }
        controller.close()
      } catch (e) {
        console.error('[mb-sw] decrypt failed:', e)
        controller.error(e)
      } finally {
        try {
          await reader.cancel()
        } catch {
          // ignore
        }
      }
    },
    cancel() {
      try {
        abortController.abort()
      } catch {
        // ignore
      }
      try {
        reader.cancel()
      } catch {
        // ignore
      }
    }
  })

  return new Response(stream, { status: isRange ? 206 : 200, headers })
}

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting())
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('message', (event) => {
  const data = event.data
  if (!data || typeof data !== 'object') return
  if (data.type !== 'mb:set-context') return

  const replyPort = (event.ports && event.ports[0]) ? event.ports[0] : null

  const pasteId = String(data.pasteId || '').trim()
  if (!pasteId) {
    if (replyPort) replyPort.postMessage({ ok: false })
    return
  }

  const keyBytes = toUint8Key(data.encryptionKeyBytes)
  if (!keyBytes || ![16, 24, 32].includes(keyBytes.byteLength)) {
    if (replyPort) replyPort.postMessage({ ok: false })
    return
  }

  const accessKey = data.accessKey ? String(data.accessKey).trim() : null
  const adminKey = data.adminKey ? String(data.adminKey).trim() : null

  event.waitUntil(
    (async () => {
      try {
        const cryptoKey = await crypto.subtle.importKey(
          'raw',
          keyBytes,
          { name: 'AES-GCM' },
          false,
          ['decrypt']
        )
        pasteContexts.set(pasteId, { keyBytes, cryptoKey, accessKey, adminKey })
        if (replyPort) replyPort.postMessage({ ok: true })
      } catch (e) {
        console.error('[mb-sw] importKey failed:', e)
        if (replyPort) replyPort.postMessage({ ok: false })
      }
    })()
  )
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  const m = MB_PLAIN_PATH_RE.exec(url.pathname)
  if (!m) return

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    event.respondWith(new Response('Method Not Allowed', { status: 405 }))
    return
  }

  const pasteId = m[1]
  const fileId = m[2]

  event.respondWith(handlePlainFileRequest(request, pasteId, fileId))
})
