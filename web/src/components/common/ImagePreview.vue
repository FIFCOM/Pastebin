<template>
  <!-- Image preview overlay (click image to open, click outside/ESC to close) -->
  <transition name="mb-image-preview">
    <div
      v-if="open"
      class="mb-image-preview-overlay"
      role="dialog"
      aria-modal="true"
      @click="close"
    >
      <div class="mb-image-preview-panel" @click.stop>
        <button
          class="mb-image-preview-close"
          type="button"
          aria-label="关闭图片预览"
          title="关闭"
          @click="close"
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
            v-if="src"
            ref="previewImgRef"
            class="mb-image-preview-img"
            :src="src"
            :alt="altText"
            :style="previewImgStyle"
            draggable="false"
            @dblclick.stop="onPreviewDblClick"
            @load="onPreviewImgLoad"
          />
        </div>
        <div v-if="loading" class="mb-image-preview-loading">加载中...</div>
        <div v-if="error" class="mb-image-preview-error">{{ error }}</div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
  src: string
  alt?: string
  loading?: boolean
  error?: string
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'close'): void
}>()

const altText = computed(() => props.alt ?? '')
const loading = computed(() => Boolean(props.loading))
const error = computed(() => props.error ?? '')

let previewTicket = 0
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

function close() {
  previewTicket += 1
  resetPreviewState()
  emit('update:open', false)
  emit('close')
}

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
    if (ticket !== previewTicket || !props.open) return
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
      if (ticket !== previewTicket || !props.open) return
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
  const img = (e?.target instanceof HTMLImageElement ? e.target : null) || previewImgRef.value
  if (!img) return
  const iw = Number(img.naturalWidth || 0)
  const ih = Number(img.naturalHeight || 0)
  if (!Number.isFinite(iw) || !Number.isFinite(ih) || iw <= 0 || ih <= 0) return
  previewNatW.value = iw
  previewNatH.value = ih
  schedulePreviewFit(previewTicket)
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
  if (!props.src) return
  if (previewNatW.value <= 0 || previewNatH.value <= 0) return

  // Trackpad: deltaY is small; mouse wheel: deltaY is larger.
  const factor = Math.exp(-e.deltaY / 260)
  const nextScale = previewScale.value * factor
  zoomPreviewAt(e.clientX, e.clientY, nextScale)
}

function onPreviewDblClick(e: MouseEvent) {
  if (!props.src) return
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
  if (!props.src) return
  if (previewNatW.value <= 0 || previewNatH.value <= 0) return
  if (e.pointerType === 'mouse' && e.button !== 0) return

  const pt = clientToViewportPoint(e.clientX, e.clientY)
  if (!pt) return

  const path = typeof e.composedPath === 'function' ? e.composedPath() : []
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
    close()
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

function onImagePreviewKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}

watch(
  () => props.open,
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

watch(
  () => [props.open, props.src] as const,
  ([open]) => {
    if (!open) {
      previewTicket += 1
      resetPreviewState()
      return
    }

    const ticket = (previewTicket += 1)
    resetPreviewState()
    schedulePreviewFit(ticket)
  },
  { flush: 'post' }
)

onBeforeUnmount(() => {
  try {
    window.removeEventListener('keydown', onImagePreviewKeyDown)
    window.removeEventListener('resize', onPreviewResize)
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

