import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

interface RestartStatusLoadOptions {
  preserveRestartView?: boolean
  silentError?: boolean
}

interface UseRestartPollingOptions {
  isRestartCardVisible: Ref<boolean>
  loadStatus: (options?: RestartStatusLoadOptions) => Promise<void>
  onTimeout: () => void
  pollIntervalMs?: number
  manualHintMs?: number
  timeoutMs?: number
}

export function useRestartPolling(options: UseRestartPollingOptions) {
  const pollIntervalMs = options.pollIntervalMs ?? 1500
  const manualHintMs = options.manualHintMs ?? 30000
  const timeoutMs = options.timeoutMs ?? 60000

  const isRestartPolling = ref(false)
  const showManualRestartHint = ref(false)
  const restartPollTimedOut = ref(false)

  let restartPollTimer: number | null = null
  let restartHintTimer: number | null = null
  let restartTimeoutTimer: number | null = null

  function resetRestartHintState() {
    showManualRestartHint.value = false
    restartPollTimedOut.value = false
  }

  function stopRestartPolling(options: { resetHintState?: boolean } = {}) {
    const { resetHintState = true } = options
    isRestartPolling.value = false

    if (resetHintState) {
      resetRestartHintState()
    }

    if (restartPollTimer !== null) {
      window.clearTimeout(restartPollTimer)
      restartPollTimer = null
    }

    if (restartHintTimer !== null) {
      window.clearTimeout(restartHintTimer)
      restartHintTimer = null
    }

    if (restartTimeoutTimer !== null) {
      window.clearTimeout(restartTimeoutTimer)
      restartTimeoutTimer = null
    }
  }

  function handleRestartPollingTimeout() {
    if (!isRestartPolling.value) return
    stopRestartPolling({ resetHintState: false })
    restartPollTimedOut.value = true
    showManualRestartHint.value = true
    options.onTimeout()
  }

  function scheduleRestartPolling(delay = pollIntervalMs) {
    if (!isRestartPolling.value || restartPollTimer !== null) return

    restartPollTimer = window.setTimeout(() => {
      restartPollTimer = null
      void pollRestartStatus()
    }, delay)
  }

  async function pollRestartStatus() {
    if (!isRestartPolling.value) return

    await options.loadStatus({ preserveRestartView: true, silentError: true })
    if (!isRestartPolling.value) return

    if (!options.isRestartCardVisible.value) {
      stopRestartPolling()
      return
    }

    scheduleRestartPolling()
  }

  function startRestartPolling() {
    if (isRestartPolling.value) return

    isRestartPolling.value = true
    resetRestartHintState()

    restartHintTimer = window.setTimeout(() => {
      showManualRestartHint.value = true
    }, manualHintMs)

    restartTimeoutTimer = window.setTimeout(() => {
      handleRestartPollingTimeout()
    }, timeoutMs)

    scheduleRestartPolling(0)
  }

  async function handleRestartCheck() {
    resetRestartHintState()

    await options.loadStatus({ preserveRestartView: true })
    if (options.isRestartCardVisible.value) {
      startRestartPolling()
    }
  }

  watch(
    options.isRestartCardVisible,
    (visible) => {
      if (visible) {
        startRestartPolling()
        return
      }

      stopRestartPolling()
    },
    { immediate: true }
  )

  onBeforeUnmount(() => {
    stopRestartPolling()
  })

  return {
    isRestartPolling,
    showManualRestartHint,
    restartPollTimedOut,
    resetRestartHintState,
    stopRestartPolling,
    startRestartPolling,
    handleRestartCheck
  }
}
