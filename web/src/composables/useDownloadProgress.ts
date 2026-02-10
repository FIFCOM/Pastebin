import { computed, ref } from 'vue'

type ProgressTotals = {
  plainTotal?: number
  encryptedTotal?: number
}

function clampNonNegativeInt(v: unknown): number {
  const n = Number(v)
  if (!Number.isFinite(n) || n <= 0) return 0
  return Math.floor(n)
}

export function useDownloadProgress() {
  const plainDone = ref(0)
  const plainTotal = ref(0)
  const encryptedDone = ref(0)
  const encryptedTotal = ref(0)

  // Smoothed speed estimate (bytes/sec), based on plain progress when available.
  const speedBps = ref(0)
  const lastSample = ref<{ ts: number; done: number } | null>(null)

  const ratio = computed(() => {
    const total = plainTotal.value > 0 ? plainTotal.value : encryptedTotal.value
    if (!Number.isFinite(total) || total <= 0) return 0
    const done = plainTotal.value > 0 ? plainDone.value : encryptedDone.value
    if (!Number.isFinite(done) || done <= 0) return 0
    return Math.min(1, Math.max(0, done / total))
  })

  const etaSeconds = computed(() => {
    const total = plainTotal.value
    const done = plainDone.value
    const speed = speedBps.value
    if (!Number.isFinite(total) || total <= 0) return null
    if (!Number.isFinite(done) || done < 0) return null
    if (!Number.isFinite(speed) || speed <= 1) return null
    if (done >= total) return 0
    return (total - done) / speed
  })

  function reset(totals?: ProgressTotals) {
    plainDone.value = 0
    encryptedDone.value = 0
    plainTotal.value = clampNonNegativeInt(totals?.plainTotal)
    encryptedTotal.value = clampNonNegativeInt(totals?.encryptedTotal)
    speedBps.value = 0
    lastSample.value = null
  }

  function updateSpeed(done: number) {
    const now = Date.now()
    const prev = lastSample.value
    if (!prev) {
      lastSample.value = { ts: now, done }
      return
    }

    const dt = (now - prev.ts) / 1000
    const dDone = done - prev.done
    if (!Number.isFinite(dt) || dt <= 0.15) return
    if (!Number.isFinite(dDone) || dDone <= 0) return

    // Only advance the sample when we actually use it; otherwise frequent updates
    // would keep resetting dt and speed would never update.
    lastSample.value = { ts: now, done }

    const inst = dDone / dt
    // Simple EMA to reduce jitter.
    const alpha = 0.2
    speedBps.value = speedBps.value > 0 ? speedBps.value * (1 - alpha) + inst * alpha : inst
  }

  function setTotals(totals: ProgressTotals) {
    if (totals.plainTotal !== undefined) plainTotal.value = clampNonNegativeInt(totals.plainTotal)
    if (totals.encryptedTotal !== undefined)
      encryptedTotal.value = clampNonNegativeInt(totals.encryptedTotal)
  }

  function onPlainProgress(done: number, total?: number) {
    plainDone.value = clampNonNegativeInt(done)
    if (total !== undefined) plainTotal.value = clampNonNegativeInt(total)
    updateSpeed(plainDone.value)
  }

  function onEncryptedProgress(done: number, total?: number) {
    encryptedDone.value = clampNonNegativeInt(done)
    if (total !== undefined) encryptedTotal.value = clampNonNegativeInt(total)
  }

  return {
    plainDone,
    plainTotal,
    encryptedDone,
    encryptedTotal,
    ratio,
    speedBps,
    etaSeconds,
    reset,
    setTotals,
    onPlainProgress,
    onEncryptedProgress
  }
}
