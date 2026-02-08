<template>
  <div ref="viewerRef" class="markdown-viewer mdui-prose" v-html="renderedHtml"></div>
  <!-- 动态主题样式 -->
  <component :is="'style'" v-text="highlightStyle"></component>

  <!-- Image preview overlay (click image to open, click outside/ESC to close) -->
  <transition name="mb-image-preview">
    <div
      v-if="imagePreviewOpen"
      class="mb-image-preview-overlay"
      role="dialog"
      aria-modal="true"
      @click="closeImagePreview"
    >
      <div class="mb-image-preview-panel" @click.stop>
        <button
          class="mb-image-preview-close"
          type="button"
          aria-label="关闭图片预览"
          title="关闭"
          @click="closeImagePreview"
        >
          X
        </button>
        <div
          ref="previewViewportRef"
          class="mb-image-preview-viewport"
          :style="{ cursor: previewCursor }"
          @wheel.prevent="onPreviewWheel"
          @pointerdown="onPreviewPointerDown"
          @pointermove="onPreviewPointerMove"
          @pointerup="onPreviewPointerUp"
          @pointercancel="onPreviewPointerUp"
        >
          <img
            v-if="imagePreviewSrc"
            ref="previewImgRef"
            class="mb-image-preview-img"
            :src="imagePreviewSrc"
            :alt="imagePreviewAlt"
            :style="previewImgStyle"
            draggable="false"
            @dblclick.stop="onPreviewDblClick"
            @load="onPreviewImgLoad"
          />
        </div>
        <div v-if="imagePreviewLoading" class="mb-image-preview-loading">加载中...</div>
        <div v-if="imagePreviewError" class="mb-image-preview-error">{{ imagePreviewError }}</div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import markdownItAnchor from 'markdown-it-anchor'
import markdownItTocDoneRight from 'markdown-it-toc-done-right'
import markdownItKatex from '@vscode/markdown-it-katex'
import { useTheme } from '@/composables/useTheme'
import { buildMbDownloadPageHref, parseMbInternalFilePath } from '@/utils/mbFile'
import type { MbFileManifest } from '@/utils/mbFileDecrypt'
import { decryptChunkedFileToBlob } from '@/utils/mbFileDecrypt'
// 导入主题样式
import lightTheme from 'highlight.js/styles/github.css?inline'
import darkTheme from 'highlight.js/styles/github-dark.css?inline'
import 'katex/dist/katex.min.css'

const props = defineProps<{
  content: string
  encryptionKey?: Uint8Array | null
  accessKey?: string | null
}>()

const { actualTheme } = useTheme()
const viewerRef = ref<HTMLElement | null>(null)

// 主题样式映射
const themeStyles = {
  light: lightTheme,
  dark: darkTheme
} as const

// 动态计算当前主题样式
const highlightStyle = computed(() => themeStyles[actualTheme.value])

// Used as a placeholder to avoid the broken-image icon before we hydrate/decrypt internal images.
const TRANSPARENT_1PX =
  'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='

// 初始化 markdown-it 实例
const md = new MarkdownIt({
  html: false,         // 不允许 HTML 标签
  linkify: true,       // 自动识别链接
  typographer: false,
  breaks: true,        // 将段内换行转换为 <br>
  highlight(str, lang) {
    // 官方文档推荐写法：优先使用指定语言，否则可选用自动检测或回退为转义文本
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
      } catch (__) {
        // ignore
      }
    }

    try {
      const result = hljs.highlightAuto(str)
      return result.value
    } catch (__) {
      // ignore
    }

    // 返回空字符串将交给 markdown-it 执行默认转义
    return ''
  }
})

// 启用 markdown-it-anchor：为标题生成 id
md.use(markdownItAnchor, {
  slugify: (s: string) =>
    encodeURIComponent(
      s
        .trim()
        .toLowerCase()
        .replace(/[\s]+/g, '-')
        .replace(/[()./?#]/g, '')
    ),
  tabIndex: false
})

// 启用 markdown-it-toc-done-right：支持 [toc] 或 ${toc} 生成目录
md.use(markdownItTocDoneRight, {
  containerClass: 'markdown-toc',
  listType: 'ul',
  level: [1, 2, 3, 4]
})

 // 启用 markdown-it-katex（VS Code 同款实现）：渲染行内/块级 LaTeX 公式
md.use(markdownItKatex, {
  throwOnError: false,
  errorColor: '#cc0000'
})

// ---- MaterialBin internal file links handling (encrypted blobs) ----
const defaultImageRenderer =
  md.renderer.rules.image ||
  ((tokens, idx, options, env, self) => {
    void env
    return self.renderToken(tokens, idx, options)
  })

md.renderer.rules.image = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  if (token) {
    // Enable browser-native lazy loading for all images by default.
    token.attrSet('loading', 'lazy')
    token.attrSet('decoding', 'async')

    const src = token.attrGet('src')
    const ref = src ? parseMbInternalFilePath(src) : null
    if (ref) {
      token.attrSet('src', TRANSPARENT_1PX)
      token.attrSet('data-mb-type', 'img')
      token.attrSet('data-mb-paste-id', ref.pasteId)
      token.attrSet('data-mb-file-id', ref.fileId)
    }
  }
  return defaultImageRenderer(tokens, idx, options, env, self)
}

const defaultLinkOpenRenderer =
  md.renderer.rules.link_open ||
  ((tokens, idx, options, env, self) => {
    void env
    return self.renderToken(tokens, idx, options)
  })

md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  if (token) {
    const href = token.attrGet('href')
    const ref = href ? parseMbInternalFilePath(href) : null
    if (ref) {
      token.attrSet(
        'href',
        buildMbDownloadPageHref(ref.pasteId, ref.fileId, { encryptionKeyHash: window.location.hash })
      )
      token.attrSet('data-mb-type', 'file')
      token.attrSet('data-mb-paste-id', ref.pasteId)
      token.attrSet('data-mb-file-id', ref.fileId)
    }
  }
  return defaultLinkOpenRenderer(tokens, idx, options, env, self)
}

// 渲染 Markdown
const renderedHtml = computed(() => {
  try {
    return md.render(props.content)
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return `<pre><code>${props.content}</code></pre>`
  }
})

// ---- Post-render: decrypt and hydrate internal encrypted images ----
const blobUrls = new Set<string>()
let io: IntersectionObserver | null = null
let generation = 0
let activeDecryptions = 0
const pendingDecryptQueue: Array<() => void> = []

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

async function loadInternalImageIfNeeded(img: HTMLImageElement, gen: number) {
  if (gen !== generation) return
  if (!img.isConnected) return
  if (img.dataset.mbType !== 'img') return
  if (img.dataset.mbStatus === 'loading' || img.dataset.mbStatus === 'done') return

  const key = props.encryptionKey ?? null
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
      accessKey: props.accessKey
    })

    if (gen !== generation || !img.isConnected) {
      try {
        URL.revokeObjectURL(url)
      } catch {
        // ignore
      }
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
}

async function hydrateEncryptedImages(root: HTMLElement, gen: number) {
  const key = props.encryptionKey ?? null
  if (!key) return

  const imgs = Array.from(root.querySelectorAll('img[data-mb-type="img"]')) as HTMLImageElement[]
  if (imgs.length === 0) return

  io?.disconnect()
  io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        const img = entry.target as HTMLImageElement
        io?.unobserve(img)

        void withConcurrencyLimit(3, async () => {
          await loadInternalImageIfNeeded(img, gen)
        })
      }
    },
    { root: null, rootMargin: '200px', threshold: 0.01 }
  )

  for (const img of imgs) io.observe(img)
}

// ---- Image preview (click-to-zoom) ----
const imagePreviewOpen = ref(false)
const imagePreviewSrc = ref('')
const imagePreviewAlt = ref('')
const imagePreviewLoading = ref(false)
const imagePreviewError = ref('')
let imagePreviewTicket = 0
let prevBodyOverflow: string | null = null

const previewViewportRef = ref<HTMLDivElement | null>(null)
const previewImgRef = ref<HTMLImageElement | null>(null)
const previewScale = ref(1)
const previewMinScale = ref(1)
const previewTx = ref(0)
const previewTy = ref(0)
const previewNatW = ref(0)
const previewNatH = ref(0)
const previewPointerCount = ref(0)

const previewImgStyle = computed(() => ({
  transform: `translate3d(${previewTx.value}px, ${previewTy.value}px, 0) scale(${previewScale.value})`
}))

const previewCursor = computed(() => {
  // mouse-only hint; on touch devices cursor is ignored.
  if (previewPointerCount.value > 0) return 'grabbing'
  if (previewScale.value > previewMinScale.value + 1e-3) return 'grab'
  return 'zoom-in'
})

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v))
}

function getPreviewViewportSize(): { w: number; h: number } | null {
  const el = previewViewportRef.value
  if (!el) return null
  // Use layout sizes (not getBoundingClientRect) so we stay stable during the
  // open/close scale transition (rect sizes are affected by CSS transforms).
  const w = Math.max(0, el.clientWidth)
  const h = Math.max(0, el.clientHeight)
  if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) return null
  return { w, h }
}

function clientToViewportPoint(clientX: number, clientY: number): { x: number; y: number } | null {
  const el = previewViewportRef.value
  if (!el) return null
  const rect = el.getBoundingClientRect()
  if (!Number.isFinite(rect.width) || !Number.isFinite(rect.height) || rect.width <= 0 || rect.height <= 0) {
    return null
  }
  const sx = el.clientWidth / rect.width
  const sy = el.clientHeight / rect.height
  return {
    x: (clientX - rect.left) * sx,
    y: (clientY - rect.top) * sy
  }
}

function computeFitScale(vw: number, vh: number, iw: number, ih: number): number {
  if (iw <= 0 || ih <= 0) return 1
  return Math.min(vw / iw, vh / ih, 1)
}

function clampPreviewTranslate(tx: number, ty: number, scale: number): { x: number; y: number } {
  const vp = getPreviewViewportSize()
  if (!vp) return { x: tx, y: ty }
  const iw = previewNatW.value
  const ih = previewNatH.value
  if (!Number.isFinite(iw) || !Number.isFinite(ih) || iw <= 0 || ih <= 0) return { x: tx, y: ty }

  const dw = iw * scale
  const dh = ih * scale

  const xMin = dw <= vp.w ? (vp.w - dw) / 2 : vp.w - dw
  const xMax = dw <= vp.w ? (vp.w - dw) / 2 : 0
  const yMin = dh <= vp.h ? (vp.h - dh) / 2 : vp.h - dh
  const yMax = dh <= vp.h ? (vp.h - dh) / 2 : 0

  return { x: clamp(tx, xMin, xMax), y: clamp(ty, yMin, yMax) }
}

function setPreviewTransform(scale: number, tx: number, ty: number) {
  const clampedScale = clamp(scale, previewMinScale.value, PREVIEW_MAX_SCALE)
  const pos = clampPreviewTranslate(tx, ty, clampedScale)
  previewScale.value = clampedScale
  previewTx.value = pos.x
  previewTy.value = pos.y
}

function schedulePreviewFit(ticket: number) {
  // Defer to ensure refs are populated and the transition/layout has a valid viewport size.
  void nextTick(() => {
    if (ticket !== imagePreviewTicket || !imagePreviewOpen.value) return
    const img = previewImgRef.value
    if (img) {
      const iw = Number(img.naturalWidth || 0)
      const ih = Number(img.naturalHeight || 0)
      if (Number.isFinite(iw) && Number.isFinite(ih) && iw > 0 && ih > 0) {
        previewNatW.value = iw
        previewNatH.value = ih
      }
    }
    window.requestAnimationFrame(() => {
      if (ticket !== imagePreviewTicket || !imagePreviewOpen.value) return
      resetPreviewTransformToFit()
    })
  })
}

function resetPreviewTransformToFit() {
  const vp = getPreviewViewportSize()
  const iw = previewNatW.value
  const ih = previewNatH.value
  if (!vp || iw <= 0 || ih <= 0) return

  const fit = computeFitScale(vp.w, vp.h, iw, ih)
  previewMinScale.value = fit
  previewScale.value = fit

  const tx = (vp.w - iw * fit) / 2
  const ty = (vp.h - ih * fit) / 2
  const pos = clampPreviewTranslate(tx, ty, fit)
  previewTx.value = pos.x
  previewTy.value = pos.y
}

function onPreviewResize() {
  const vp = getPreviewViewportSize()
  const iw = previewNatW.value
  const ih = previewNatH.value
  if (!vp || iw <= 0 || ih <= 0) return

  const oldFit = previewMinScale.value
  const newFit = computeFitScale(vp.w, vp.h, iw, ih)
  previewMinScale.value = newFit

  // If we're at (or very close to) the old fit, re-fit on resize.
  if (Math.abs(previewScale.value - oldFit) < 1e-3) {
    resetPreviewTransformToFit()
    return
  }

  // Otherwise keep the current zoom level, but clamp to the new viewport bounds.
  const nextScale = Math.max(previewScale.value, newFit)
  const pos = clampPreviewTranslate(previewTx.value, previewTy.value, nextScale)
  previewScale.value = nextScale
  previewTx.value = pos.x
  previewTy.value = pos.y
}

function resetPreviewState() {
  previewPointers.clear()
  previewPointerStarts.clear()
  pinchState.active = false
  previewNatW.value = 0
  previewNatH.value = 0
  previewScale.value = 1
  previewMinScale.value = 1
  previewTx.value = 0
  previewTy.value = 0
  previewPointerCount.value = 0
  lastTap.ts = 0
}

function onPreviewImgLoad(e?: Event) {
  const img =
    (e?.target instanceof HTMLImageElement ? e.target : null) ||
    previewImgRef.value
  if (!img) return
  const iw = Number(img.naturalWidth || 0)
  const ih = Number(img.naturalHeight || 0)
  if (!Number.isFinite(iw) || !Number.isFinite(ih) || iw <= 0 || ih <= 0) return
  previewNatW.value = iw
  previewNatH.value = ih
  schedulePreviewFit(imagePreviewTicket)
}

function zoomPreviewAt(clientX: number, clientY: number, nextScale: number) {
  const pt = clientToViewportPoint(clientX, clientY)
  if (!pt) return
  const anchorX = pt.x
  const anchorY = pt.y

  const oldScale = previewScale.value
  const clampedNextScale = clamp(nextScale, previewMinScale.value, PREVIEW_MAX_SCALE)
  if (Math.abs(clampedNextScale - oldScale) < 1e-6) return

  // Keep the image point under (anchorX, anchorY) stationary while zooming.
  const imgX = (anchorX - previewTx.value) / oldScale
  const imgY = (anchorY - previewTy.value) / oldScale
  const nextTx = anchorX - imgX * clampedNextScale
  const nextTy = anchorY - imgY * clampedNextScale
  setPreviewTransform(clampedNextScale, nextTx, nextTy)
}

function onPreviewWheel(e: WheelEvent) {
  // Only zoom when we have a loaded image and viewport.
  if (!imagePreviewSrc.value) return
  if (previewNatW.value <= 0 || previewNatH.value <= 0) return

  // Trackpad: deltaY is small; mouse wheel: deltaY is larger.
  const factor = Math.exp(-e.deltaY / 260)
  const nextScale = previewScale.value * factor
  zoomPreviewAt(e.clientX, e.clientY, nextScale)
}

function onPreviewDblClick(e: MouseEvent) {
  if (!imagePreviewSrc.value) return
  if (previewNatW.value <= 0 || previewNatH.value <= 0) return

  const isZoomed = previewScale.value > previewMinScale.value + 1e-3
  if (isZoomed) {
    resetPreviewTransformToFit()
  } else {
    zoomPreviewAt(e.clientX, e.clientY, previewMinScale.value * 2)
  }
}

// --- Pointer-based pan + pinch-to-zoom (works on desktop + mobile) ---
const PREVIEW_MAX_SCALE = 8
const previewPointers = new Map<number, { x: number; y: number }>() // viewport-local coords
const previewPointerStarts = new Map<number, { x: number; y: number; onImg: boolean; moved: boolean }>()
const pinchState = {
  active: false,
  startDist: 0,
  startScale: 1,
  // image point under the pinch center, in image coordinates (before scaling)
  imgX: 0,
  imgY: 0
}
let dragStartClientX = 0
let dragStartClientY = 0
let dragStartTx = 0
let dragStartTy = 0

const lastTap = { ts: 0, x: 0, y: 0 }
const DOUBLE_TAP_MS = 280
const DOUBLE_TAP_DIST_PX = 26
const TAP_MOVE_THRESHOLD_PX = 8

function onPreviewPointerDown(e: PointerEvent) {
  if (!imagePreviewSrc.value) return
  if (previewNatW.value <= 0 || previewNatH.value <= 0) return
  if (e.pointerType === 'mouse' && e.button !== 0) return

  const pt = clientToViewportPoint(e.clientX, e.clientY)
  if (!pt) return

  const path = (typeof e.composedPath === 'function') ? e.composedPath() : []
  const imgEl = previewImgRef.value
  const onImg = !!(imgEl && path.includes(imgEl))
  previewPointerStarts.set(e.pointerId, { x: pt.x, y: pt.y, onImg, moved: false })
  previewPointers.set(e.pointerId, { x: pt.x, y: pt.y })
  previewPointerCount.value = previewPointers.size
  try {
    previewViewportRef.value?.setPointerCapture(e.pointerId)
  } catch {
    // ignore
  }

  if (previewPointers.size === 1) {
    pinchState.active = false
    dragStartClientX = pt.x
    dragStartClientY = pt.y
    dragStartTx = previewTx.value
    dragStartTy = previewTy.value
  } else if (previewPointers.size === 2) {
    const pts = Array.from(previewPointers.values())
    const p1 = { x: pts[0]!.x, y: pts[0]!.y }
    const p2 = { x: pts[1]!.x, y: pts[1]!.y }
    const cx = (p1.x + p2.x) / 2
    const cy = (p1.y + p2.y) / 2
    const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y)
    if (!Number.isFinite(dist) || dist <= 0) return

    pinchState.active = true
    pinchState.startDist = dist
    pinchState.startScale = previewScale.value
    pinchState.imgX = (cx - previewTx.value) / previewScale.value
    pinchState.imgY = (cy - previewTy.value) / previewScale.value
  }
}

function onPreviewPointerMove(e: PointerEvent) {
  if (!previewPointers.has(e.pointerId)) return
  const pt = clientToViewportPoint(e.clientX, e.clientY)
  if (!pt) return
  const start = previewPointerStarts.get(e.pointerId)
  if (start && !start.moved) {
    const dist = Math.hypot(pt.x - start.x, pt.y - start.y)
    if (dist >= TAP_MOVE_THRESHOLD_PX) start.moved = true
  }
  previewPointers.set(e.pointerId, { x: pt.x, y: pt.y })

  if (previewPointers.size === 1 && !pinchState.active) {
    const dx = pt.x - dragStartClientX
    const dy = pt.y - dragStartClientY
    setPreviewTransform(previewScale.value, dragStartTx + dx, dragStartTy + dy)
    return
  }

  if (previewPointers.size === 2) {
    const pts = Array.from(previewPointers.values())
    const p1 = { x: pts[0]!.x, y: pts[0]!.y }
    const p2 = { x: pts[1]!.x, y: pts[1]!.y }
    const cx = (p1.x + p2.x) / 2
    const cy = (p1.y + p2.y) / 2
    const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y)
    if (!Number.isFinite(dist) || dist <= 0) return

    if (!pinchState.active) {
      pinchState.active = true
      pinchState.startDist = dist
      pinchState.startScale = previewScale.value
      pinchState.imgX = (cx - previewTx.value) / previewScale.value
      pinchState.imgY = (cy - previewTy.value) / previewScale.value
    }

    const rawScale = pinchState.startScale * (dist / pinchState.startDist)
    const nextScale = clamp(rawScale, previewMinScale.value, PREVIEW_MAX_SCALE)
    const nextTx = cx - pinchState.imgX * nextScale
    const nextTy = cy - pinchState.imgY * nextScale
    setPreviewTransform(nextScale, nextTx, nextTy)
  }
}

function onPreviewPointerUp(e: PointerEvent) {
  const wasTouch = e.pointerType === 'touch'
  const prevCount = previewPointers.size
  const start = previewPointerStarts.get(e.pointerId) || null

  previewPointerStarts.delete(e.pointerId)
  previewPointers.delete(e.pointerId)
  previewPointerCount.value = previewPointers.size

  if (previewPointers.size < 2) {
    pinchState.active = false
  }

  if (previewPointers.size === 1) {
    // Continue panning with the remaining pointer.
    const remaining = Array.from(previewPointers.values())[0]!
    dragStartClientX = remaining.x
    dragStartClientY = remaining.y
    dragStartTx = previewTx.value
    dragStartTy = previewTy.value
  }

  if (prevCount === 1 && previewPointers.size === 0 && start && !start.moved && !start.onImg) {
    // Tap on background closes the preview (both desktop + mobile).
    closeImagePreview()
    return
  }

  if (wasTouch && prevCount === 1 && previewPointers.size === 0 && start && !start.moved && start.onImg) {
    // Double-tap to toggle zoom on mobile (image only).
    const now = Date.now()
    const dt = now - lastTap.ts
    const dist = Math.hypot(e.clientX - lastTap.x, e.clientY - lastTap.y)
    if (dt > 0 && dt <= DOUBLE_TAP_MS && dist <= DOUBLE_TAP_DIST_PX) {
      lastTap.ts = 0
      // Toggle fit <-> 2x at tap point.
      const isZoomed = previewScale.value > previewMinScale.value + 1e-3
      if (isZoomed) {
        resetPreviewTransformToFit()
      } else {
        zoomPreviewAt(e.clientX, e.clientY, previewMinScale.value * 2)
      }
    } else {
      lastTap.ts = now
      lastTap.x = e.clientX
      lastTap.y = e.clientY
    }
  }
}

function closeImagePreview() {
  imagePreviewTicket += 1
  resetPreviewState()
  imagePreviewOpen.value = false
  imagePreviewSrc.value = ''
  imagePreviewAlt.value = ''
  imagePreviewLoading.value = false
  imagePreviewError.value = ''
}

function onImagePreviewKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') closeImagePreview()
}

watch(
  imagePreviewOpen,
  (open) => {
    if (open) {
      window.addEventListener('keydown', onImagePreviewKeyDown)
      window.addEventListener('resize', onPreviewResize)
      // Lock body scroll while overlay is open.
      if (prevBodyOverflow === null) prevBodyOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
    } else {
      window.removeEventListener('keydown', onImagePreviewKeyDown)
      window.removeEventListener('resize', onPreviewResize)
      if (prevBodyOverflow !== null) {
        document.body.style.overflow = prevBodyOverflow
        prevBodyOverflow = null
      }
    }
  },
  { flush: 'post' }
)

async function openImagePreview(img: HTMLImageElement) {
  const ticket = (imagePreviewTicket += 1)

  resetPreviewState()
  imagePreviewAlt.value = img.getAttribute('alt') || img.getAttribute('title') || ''
  imagePreviewError.value = ''
  imagePreviewLoading.value = true
  imagePreviewOpen.value = true
  imagePreviewSrc.value = img.currentSrc || img.src || ''

  // If the thumbnail is already loaded, use its natural size so we can fit/center
  // immediately, even if the preview <img> load event fires before refs are set.
  const thumbW = Number(img.naturalWidth || 0)
  const thumbH = Number(img.naturalHeight || 0)
  if (Number.isFinite(thumbW) && Number.isFinite(thumbH) && thumbW > 0 && thumbH > 0) {
    previewNatW.value = thumbW
    previewNatH.value = thumbH
  }
  schedulePreviewFit(ticket)

  const gen = generation

  // Internal encrypted images: ensure we have a decrypted blob URL before showing.
  if (img.dataset.mbType === 'img') {
    const key = props.encryptionKey ?? null
    if (!key) {
      imagePreviewLoading.value = false
      imagePreviewError.value = '缺少解密密钥，无法预览该图片'
      imagePreviewSrc.value = ''
      return
    }

    // Attempt to start decryption if not already started.
    await withConcurrencyLimit(3, async () => {
      await loadInternalImageIfNeeded(img, gen)
    })

    // If another hydration is in-flight, wait for it to finish (or error/timeout).
    const start = Date.now()
    while (img.dataset.mbStatus === 'loading') {
      if (ticket !== imagePreviewTicket || !imagePreviewOpen.value) return
      if (gen !== generation || !img.isConnected) return
      if (Date.now() - start > 15000) break
      await new Promise((r) => window.setTimeout(r, 120))
    }

    if (ticket !== imagePreviewTicket || !imagePreviewOpen.value) return
    if (img.dataset.mbStatus === 'done') {
      imagePreviewSrc.value = img.currentSrc || img.src || ''
      imagePreviewLoading.value = false
      return
    }
    if (img.dataset.mbStatus === 'error') {
      imagePreviewLoading.value = false
      imagePreviewError.value = '图片解密失败，可点击链接下载'
      imagePreviewSrc.value = ''
      return
    }
  }

  // External images: just display the full-size source URL (we only scale via CSS in the viewer).
  imagePreviewSrc.value = img.currentSrc || img.src || ''
  imagePreviewLoading.value = false
}

// 挂载后拦截 TOC 内部链接点击，避免修改 URL hash
onMounted(() => {
  const handleClick = (event: MouseEvent) => {
    const target = event.target instanceof HTMLElement ? event.target : null
    if (!target) return

    const img = target.closest('img') as HTMLImageElement | null
    if (img && viewerRef.value?.contains(img)) {
      // Keep Ctrl/Cmd-click behavior for linked images.
      const imgLink = img.closest('a')
      if (imgLink && (event.ctrlKey || event.metaKey)) return

      // Click-to-zoom image preview (also works for external images).
      event.preventDefault()
      void openImagePreview(img)
      return
    }

    const anchor = target.closest('a')
    
    if (!anchor) return
    
    const href = anchor.getAttribute('href')
    if (!href || !href.startsWith('#')) return
    
    // 阻止默认的 hash 跳转行为
    event.preventDefault()
    
    // 提取目标 id
    const targetId = href.slice(1)
    if (!targetId) return
    
    // 查找目标元素
    const targetElement = viewerRef.value?.querySelector(`#${CSS.escape(targetId)}`)
    if (!targetElement) return
    
    // 平滑滚动到目标位置，不修改 URL
    targetElement.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })
  }
  
  viewerRef.value?.addEventListener('click', handleClick)
  
  onBeforeUnmount(() => {
    viewerRef.value?.removeEventListener('click', handleClick)
  })
})

watch(
  [renderedHtml, () => props.encryptionKey, () => props.accessKey],
  async () => {
    generation += 1
    const gen = generation

    // DOM updated (v-html)
    await nextTick()

    revokeAllBlobUrls()
    if (!viewerRef.value) return

    await hydrateEncryptedImages(viewerRef.value, gen)
  },
  { flush: 'post', immediate: true }
)

onBeforeUnmount(() => {
  io?.disconnect()
  io = null
  revokeAllBlobUrls()
  // Ensure global listeners/styles are cleaned up.
  try {
    window.removeEventListener('keydown', onImagePreviewKeyDown)
  } catch {
    // ignore
  }
  if (prevBodyOverflow !== null) {
    document.body.style.overflow = prevBodyOverflow
    prevBodyOverflow = null
  }
})
</script>

<style scoped>
/* 全局 Markdown 容器基础样式，遵循 MDUI 配色与排版建议 */
.markdown-viewer {
  background-color: var(--mdui-color-surface-variant);
  border-radius: 8px;
  color: var(--mdui-color-on-surface);
  line-height: 1.7;
  font-size: 0.95rem;
  overflow-x: auto;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

/* 标题样式 */
.markdown-viewer :deep(h1),
.markdown-viewer :deep(h2),
.markdown-viewer :deep(h3),
.markdown-viewer :deep(h4),
.markdown-viewer :deep(h5),
.markdown-viewer :deep(h6) {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.25;
  color: var(--mdui-color-on-surface);
  /* 为锚点跳转预留顶栏空间，避免标题被遮挡 */
  scroll-margin-top: 80px;
}

.markdown-viewer :deep(h1) {
  font-size: 2em;
  border-bottom: 1px solid var(--mdui-color-outline-variant);
  padding-bottom: 0.3em;
}

.markdown-viewer :deep(h2) {
  font-size: 1.5em;
  border-bottom: 1px solid var(--mdui-color-outline-variant);
  padding-bottom: 0.3em;
}

.markdown-viewer :deep(h3) {
  font-size: 1.25em;
}

.markdown-viewer :deep(h4) {
  font-size: 1em;
}

.markdown-viewer :deep(h5) {
  font-size: 0.875em;
}

.markdown-viewer :deep(h6) {
  font-size: 0.85em;
  color: var(--mdui-color-on-surface-variant);
}

/* 段落样式 */
.markdown-viewer :deep(p) {
  margin-top: 0;
  margin-bottom: 1em;
  color: var(--mdui-color-on-surface);
}

/* 链接样式 */
.markdown-viewer :deep(a) {
  color: rgb(var(--mdui-color-primary));
  text-decoration: none;
  border-bottom: none;
}

.markdown-viewer :deep(a:hover) {
  text-decoration: underline;
  border-bottom: none;
}

/* 列表样式 */
.markdown-viewer :deep(ul),
.markdown-viewer :deep(ol) {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 1em;
}

.markdown-viewer :deep(li) {
  margin-bottom: 0.25em;
}

/* 行内代码样式：与 Plain.vue 一致使用 MDUI surface-container 背景，统一视觉 */
.markdown-viewer :deep(code) {
  background-color: rgb(var(--mdui-color-surface-container));
  padding: 0.15em 0.35em;
  border-radius: 4px;
  font-family:
    "Fira Code",
    Menlo,
    Monaco,
    Consolas,
    "Liberation Mono",
    "SF Mono",
    /* CJK 字体，保证中文、标点正常显示 */
    "SF Pro SC",
    "PingFang SC",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    monospace;
  font-size: 0.9em;
  color: var(--mdui-color-on-surface);
}

/* 多行代码块样式：与 Plain.vue 一致使用 MDUI surface-container 背景，统一视觉 */
.markdown-viewer :deep(pre) {
  background-color: rgb(var(--mdui-color-surface-container));
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1em 0;
  font-family:
    "Fira Code",
    Menlo,
    Monaco,
    Consolas,
    "Liberation Mono",
    "SF Mono",
    "SF Pro SC",
    "PingFang SC",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    monospace;
  font-size: 0.875em;
  line-height: 1.7;
}

.markdown-viewer :deep(pre code) {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
  font-size: 0.875em;
  font-family: inherit;
}

/* 引用样式 */
.markdown-viewer :deep(blockquote) {
  padding-left: 1em;
  margin-left: 0;
  margin-right: 0;
  color: var(--mdui-color-on-surface-variant);
}

/* 水平线样式 */
.markdown-viewer :deep(hr) {
  border: none;
  border-top: 1px solid var(--mdui-color-outline-variant);
  margin: 2em 0;
}

/* 表格样式 */
.markdown-viewer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}

.markdown-viewer :deep(th),
.markdown-viewer :deep(td) {
  border: 1px solid var(--mdui-color-outline-variant);
  padding: 0.5em 1em;
  text-align: left;
}

.markdown-viewer :deep(th) {
  background-color: var(--mdui-color-surface);
  font-weight: 600;
}

.markdown-viewer :deep(tr:nth-child(even)) {
  background-color: var(--mdui-color-surface);
}

/* 图片样式 */
.markdown-viewer :deep(img) {
  /* Limit preview size; click to open full-size overlay. */
  max-width: min(100%, var(--mb-md-img-preview-max-width, 720px));
  max-height: var(--mb-md-img-preview-max-height, 360px);
  height: auto;
  border-radius: 8px;
  cursor: zoom-in;
  object-fit: contain;
}

/* Only treat stand-alone images as block-level to avoid breaking inline images inside text. */
.markdown-viewer :deep(p > img:only-child) {
  display: block;
  margin: 1em auto;
}

/* 强调样式 */
.markdown-viewer :deep(strong) {
  font-weight: 600;
}

.markdown-viewer :deep(em) {
  font-style: italic;
}

/* 删除线样式 */
.markdown-viewer :deep(del) {
  text-decoration: line-through;
}

/* Full-size image preview overlay */
.mb-image-preview-enter-active,
.mb-image-preview-leave-active {
  transition: opacity 180ms cubic-bezier(0.2, 0, 0, 1);
}

.mb-image-preview-enter-from,
.mb-image-preview-leave-to {
  opacity: 0;
}

.mb-image-preview-enter-to,
.mb-image-preview-leave-from {
  opacity: 1;
}

.mb-image-preview-enter-from .mb-image-preview-panel,
.mb-image-preview-leave-to .mb-image-preview-panel {
  transform: scale(0.96);
}

.mb-image-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.72);
}

.mb-image-preview-panel {
  position: relative;
  width: calc(100vw - 48px);
  height: calc(100vh - 48px);
  max-width: 100%;
  max-height: 100%;
  transform: scale(1);
  transition: transform 180ms cubic-bezier(0.2, 0, 0, 1);
}

.mb-image-preview-close {
  position: absolute;
  right: 10px;
  top: 10px;
  z-index: 2;
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(0, 0, 0, 0.55);
  color: rgba(255, 255, 255, 0.95);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  user-select: none;
}

.mb-image-preview-close:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.75);
  outline-offset: 2px;
}

.mb-image-preview-viewport {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 10px;
  background-color: rgb(var(--mdui-color-surface-container));
  touch-action: none; /* enable our custom pinch/pan */
  user-select: none;
}

.mb-image-preview-img {
  position: absolute;
  left: 0;
  top: 0;
  max-width: none;
  max-height: none;
  width: auto;
  height: auto;
  display: block;
  transform-origin: 0 0;
  will-change: transform;
  -webkit-user-drag: none;
}

.mb-image-preview-loading {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  padding: 0.5rem 0.75rem;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.6);
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.875rem;
}

.mb-image-preview-error {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  padding: 0.75rem 1rem;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.875rem;
  max-width: min(90vw, 520px);
  text-align: center;
}
</style>
