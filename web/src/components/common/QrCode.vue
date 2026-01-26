<template>
  <canvas ref="canvasEl" class="qr-canvas"></canvas>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'

type EcLevel = 'L' | 'M' | 'Q' | 'H'

const props = withDefaults(
  defineProps<{
    value: string
    size?: number
    margin?: number
    errorCorrectionLevel?: EcLevel
  }>(),
  {
    size: 180,
    margin: 1,
    errorCorrectionLevel: 'M'
  }
)

const canvasEl = ref<HTMLCanvasElement | null>(null)

async function render() {
  const canvas = canvasEl.value
  if (!canvas) return

  const text = props.value?.trim()
  if (!text) {
    const ctx = canvas.getContext('2d')
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
    return
  }

  const dpr = window.devicePixelRatio || 1
  const px = Math.max(1, Math.round(props.size * dpr))
  canvas.width = px
  canvas.height = px
  canvas.style.width = `${props.size}px`
  canvas.style.height = `${props.size}px`

  await QRCode.toCanvas(canvas, text, {
    width: px,
    margin: props.margin,
    errorCorrectionLevel: props.errorCorrectionLevel
  })
}

watch(
  () => [props.value, props.size, props.margin, props.errorCorrectionLevel] as const,
  () => void render(),
  { immediate: true }
)

// When the component is created under a v-if with an already-available value,
// the initial watch runs before the canvas ref is set. Render once after mount.
onMounted(() => void render())
</script>

<style scoped>
.qr-canvas {
  display: block;
}
</style>
