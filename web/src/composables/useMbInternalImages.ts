import type { MbFileManifest } from '@/utils/mbFileDecrypt'
import { decryptChunkedFileToBlob } from '@/utils/mbFileDecrypt'

type MbInternalImagesOptions = {
  getEncryptionKey: () => Uint8Array | null
  getAccessKey: () => string | null
  /**
   * Max number of concurrent decryptions. Too high can stall the UI thread on
   * slower devices.
   */
  concurrency?: number
}

// ---- Persistent cache for internal encrypted images (stores encrypted bytes + manifest) ----
// Note: we cache *encrypted* payloads only; the decrypted blob URL is still generated per session.
const INTERNAL_IMG_CACHE_NAME = 'mb:internal-img:v1'
const INTERNAL_IMG_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000
const INTERNAL_IMG_CACHE_MAX_BYTES = 12 * 1024 * 1024
const accessKeyHashMemo = new Map<string, Promise<string>>()
const textEncoder = new TextEncoder()

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

async function getAccessKeyHash(accessKey?: string | null): Promise<string> {
  const key = accessKey?.trim() ?? ''
  if (!key) return 'none'

  const cached = accessKeyHashMemo.get(key)
  if (cached) return await cached

  const p = (async () => {
    try {
      const digest = await crypto.subtle.digest('SHA-256', textEncoder.encode(key))
      // Shorten to reduce key length (still plenty to avoid collisions for our use).
      return bytesToHex(new Uint8Array(digest).slice(0, 12))
    } catch {
      return 'none'
    }
  })()
  accessKeyHashMemo.set(key, p)
  return await p
}

async function openInternalImgCache(): Promise<Cache | null> {
  if (!('caches' in window)) return null
  try {
    return await caches.open(INTERNAL_IMG_CACHE_NAME)
  } catch {
    return null
  }
}

function isInternalCacheFresh(resp: Response): boolean {
  const ts = Number(resp.headers.get('X-MB-Cached-At') || '0')
  if (!Number.isFinite(ts) || ts <= 0) return true
  return Date.now() - ts <= INTERNAL_IMG_CACHE_TTL_MS
}

async function buildInternalCacheRequest(
  kind: 'manifest' | 'file',
  pasteId: string,
  fileId: string,
  accessKey?: string | null
): Promise<Request> {
  const ak = await getAccessKeyHash(accessKey)
  return new Request(
    `/_mb_cache/internal/${kind}/p/${encodeURIComponent(pasteId)}/f/${encodeURIComponent(fileId)}/ak/${ak}`
  )
}

async function internalCacheMatch(req: Request): Promise<Response | null> {
  const cache = await openInternalImgCache()
  if (!cache) return null
  try {
    const resp = await cache.match(req)
    if (!resp) return null
    if (!isInternalCacheFresh(resp)) {
      await cache.delete(req)
      return null
    }
    return resp
  } catch {
    return null
  }
}

async function internalCachePut(req: Request, resp: Response): Promise<void> {
  const cache = await openInternalImgCache()
  if (!cache) return
  try {
    await cache.put(req, resp)
  } catch {
    // ignore
  }
}

async function internalCacheDelete(req: Request): Promise<void> {
  const cache = await openInternalImgCache()
  if (!cache) return
  try {
    await cache.delete(req)
  } catch {
    // ignore
  }
}

function buildAccessKeyQuery(accessKey?: string | null): string {
  const key = accessKey?.trim()
  if (!key) return ''
  return `?access_key=${encodeURIComponent(key)}`
}

async function fetchManifest(pasteId: string, fileId: string, accessKey?: string | null): Promise<MbFileManifest> {
  const cacheReq = await buildInternalCacheRequest('manifest', pasteId, fileId, accessKey)
  const cached = await internalCacheMatch(cacheReq)
  if (cached) {
    try {
      return (await cached.json()) as MbFileManifest
    } catch {
      // ignore corrupted cache entry
      void internalCacheDelete(cacheReq)
    }
  }

  const resp = await fetch(
    `/api/pastes/${encodeURIComponent(pasteId)}/files/${encodeURIComponent(fileId)}/manifest${buildAccessKeyQuery(
      accessKey
    )}`
  )
  if (!resp.ok) {
    throw new Error(`manifest获取失败: HTTP ${resp.status}`)
  }

  const manifest = (await resp.json()) as MbFileManifest
  void internalCachePut(
    cacheReq,
    new Response(JSON.stringify(manifest), {
      headers: {
        'Content-Type': 'application/json',
        'X-MB-Cached-At': String(Date.now())
      }
    })
  )
  return manifest
}

async function decryptInternalImageToBlobUrl(params: {
  pasteId: string
  fileId: string
  encryptionKey: Uint8Array
  accessKey?: string | null
}): Promise<{ url: string; mimeType: string }> {
  const manifest = await fetchManifest(params.pasteId, params.fileId, params.accessKey)

  const fileCacheReq = await buildInternalCacheRequest('file', params.pasteId, params.fileId, params.accessKey)
  const cachedFile = await internalCacheMatch(fileCacheReq)
  if (cachedFile) {
    const mimeType = cachedFile.headers.get('Content-Type') || 'application/octet-stream'
    try {
      const encryptedBytes = new Uint8Array(await cachedFile.arrayBuffer())
      const encryptedStream = new Blob([encryptedBytes]).stream() as ReadableStream<Uint8Array>
      const blob = await decryptChunkedFileToBlob(
        encryptedStream,
        manifest,
        params.encryptionKey,
        { pasteId: params.pasteId, fileId: params.fileId },
        mimeType
      )
      const url = URL.createObjectURL(blob)
      return { url, mimeType }
    } catch {
      // If cache got corrupted, drop it and fall back to network.
      void internalCacheDelete(fileCacheReq)
    }
  }

  const fileResp = await fetch(
    `/api/pastes/${encodeURIComponent(params.pasteId)}/files/${encodeURIComponent(params.fileId)}${buildAccessKeyQuery(
      params.accessKey
    )}`
  )
  if (!fileResp.ok) {
    throw new Error(`文件获取失败: HTTP ${fileResp.status}`)
  }

  const mimeType = fileResp.headers.get('Content-Type') || 'application/octet-stream'

  // Cache small encrypted images to avoid re-downloading after refresh.
  const contentLen = Number(fileResp.headers.get('Content-Length') || 'NaN')
  const shouldCache =
    Number.isFinite(contentLen) && contentLen > 0 && contentLen <= INTERNAL_IMG_CACHE_MAX_BYTES

  if (shouldCache) {
    const encryptedBytes = new Uint8Array(await fileResp.arrayBuffer())
    void internalCachePut(
      fileCacheReq,
      new Response(encryptedBytes, {
        headers: {
          'Content-Type': mimeType,
          'X-MB-Cached-At': String(Date.now())
        }
      })
    )
    const encryptedStream = new Blob([encryptedBytes]).stream() as ReadableStream<Uint8Array>
    const blob = await decryptChunkedFileToBlob(
      encryptedStream,
      manifest,
      params.encryptionKey,
      { pasteId: params.pasteId, fileId: params.fileId },
      mimeType
    )
    const url = URL.createObjectURL(blob)
    return { url, mimeType }
  }

  // Prefer stream decryption when possible.
  if (fileResp.body) {
    const blob = await decryptChunkedFileToBlob(
      fileResp.body,
      manifest,
      params.encryptionKey,
      { pasteId: params.pasteId, fileId: params.fileId },
      mimeType
    )
    const url = URL.createObjectURL(blob)
    return { url, mimeType }
  }

  // Fallback: arrayBuffer.
  const encryptedBytes = new Uint8Array(await fileResp.arrayBuffer())
  const encryptedStream = new Blob([encryptedBytes]).stream() as ReadableStream<Uint8Array>
  const blob = await decryptChunkedFileToBlob(
    encryptedStream,
    manifest,
    params.encryptionKey,
    { pasteId: params.pasteId, fileId: params.fileId },
    mimeType
  )
  const url = URL.createObjectURL(blob)
  return { url, mimeType }
}

export function useMbInternalImages(opts: MbInternalImagesOptions) {
  const concurrency =
    Number.isFinite(opts.concurrency) && (opts.concurrency as number) > 0 ? (opts.concurrency as number) : 3

  const blobUrls = new Set<string>()
  let io: IntersectionObserver | null = null
  let generation = 0

  let activeDecryptions = 0
  const pendingDecryptQueue: Array<() => void> = []

  const inflight = new WeakMap<HTMLImageElement, Promise<void>>()

  function bumpGeneration(): number {
    generation += 1
    return generation
  }

  function getGeneration(): number {
    return generation
  }

  function disconnectObserver() {
    io?.disconnect()
    io = null
  }

  function revokeAllBlobUrls() {
    for (const url of blobUrls) {
      try {
        URL.revokeObjectURL(url)
      } catch {
        // ignore
      }
    }
    blobUrls.clear()
  }

  function dispose() {
    disconnectObserver()
    revokeAllBlobUrls()
  }

  async function withConcurrencyLimit<T>(limit: number, fn: () => Promise<T>): Promise<T> {
    if (activeDecryptions >= limit) {
      await new Promise<void>((resolve) => pendingDecryptQueue.push(resolve))
    }
    activeDecryptions += 1
    try {
      return await fn()
    } finally {
      activeDecryptions -= 1
      const next = pendingDecryptQueue.shift()
      next?.()
    }
  }

  async function ensureInternalImageLoaded(img: HTMLImageElement, gen: number): Promise<void> {
    if (gen !== generation) return
    if (!img.isConnected) return
    if (img.dataset.mbType !== 'img') return

    if (img.dataset.mbStatus === 'done') return

    const existing = inflight.get(img)
    if (existing) {
      await existing
      return
    }

    // If a previous run got canceled mid-flight, it may leave `data-mb-status="loading"`
    // without an in-flight promise. Treat it as stale and retry.
    if (img.dataset.mbStatus === 'loading') {
      delete img.dataset.mbStatus
    }

    const p = withConcurrencyLimit(concurrency, async () => {
      const key = opts.getEncryptionKey()
      if (!key) return

      const pasteId = img.dataset.mbPasteId ?? img.dataset.mbPasteID ?? ''
      const fileId = img.dataset.mbFileId ?? img.dataset.mbFileID ?? ''
      if (!pasteId || !fileId) return

      img.dataset.mbStatus = 'loading'
      try {
        const { url } = await decryptInternalImageToBlobUrl({
          pasteId,
          fileId,
          encryptionKey: key,
          accessKey: opts.getAccessKey()
        })

        if (gen !== generation || !img.isConnected) {
          try {
            URL.revokeObjectURL(url)
          } catch {
            // ignore
          }
          // Allow a retry in the new generation.
          if (img.isConnected) delete img.dataset.mbStatus
          return
        }

        blobUrls.add(url)
        img.src = url
        img.dataset.mbStatus = 'done'
      } catch (e) {
        console.error('图片解密失败:', e)
        img.dataset.mbStatus = 'error'
        img.title = '图片解密失败，可点击链接下载'
      }
    }).finally(() => {
      inflight.delete(img)
    })

    inflight.set(img, p)
    await p
  }

  async function hydrateEncryptedImages(root: HTMLElement, gen: number): Promise<void> {
    const key = opts.getEncryptionKey()
    if (!key) return

    const imgs = Array.from(root.querySelectorAll('img[data-mb-type="img"]')) as HTMLImageElement[]
    if (imgs.length === 0) return

    disconnectObserver()
    io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          const img = entry.target as HTMLImageElement
          io?.unobserve(img)

          void ensureInternalImageLoaded(img, gen)
        }
      },
      { root: null, rootMargin: '200px', threshold: 0.01 }
    )

    for (const img of imgs) io.observe(img)
  }

  async function ensureDecryptedForPreview(img: HTMLImageElement, gen: number): Promise<void> {
    // Preview wants to "force" the decrypt to start even if the image hasn't
    // intersected yet; we share the same limiter and inflight de-dupe.
    await ensureInternalImageLoaded(img, gen)
  }

  return {
    bumpGeneration,
    getGeneration,
    revokeAllBlobUrls,
    hydrateEncryptedImages,
    ensureInternalImageLoaded,
    ensureDecryptedForPreview,
    dispose
  }
}
