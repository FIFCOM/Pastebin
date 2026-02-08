const MB_SW_URL = '/mb-sw.js'

export type MbSwSetContextMessage = {
  type: 'mb:set-context'
  pasteId: string
  encryptionKeyBytes: number[]
  accessKey: string | null
  adminKey: string | null
}

export function buildMbPlainFilePath(pasteId: string, fileId: string): string {
  return `/mb/plain/pastes/${encodeURIComponent(pasteId)}/files/${encodeURIComponent(fileId)}`
}

export async function registerMbServiceWorker(): Promise<void> {
  if (!('serviceWorker' in navigator)) return
  try {
    // Register early; the worker uses skipWaiting + clients.claim to take control ASAP.
    await navigator.serviceWorker.register(MB_SW_URL, { scope: '/' })
  } catch (e) {
    console.warn('Failed to register MaterialBin service worker:', e)
  }
}

async function waitForController(timeoutMs: number = 8000): Promise<ServiceWorker | null> {
  if (!('serviceWorker' in navigator)) return null
  if (navigator.serviceWorker.controller) return navigator.serviceWorker.controller

  return await new Promise<ServiceWorker | null>((resolve) => {
    let done = false
    const timer = window.setTimeout(() => {
      if (done) return
      done = true
      navigator.serviceWorker.removeEventListener('controllerchange', onChange)
      resolve(navigator.serviceWorker.controller)
    }, timeoutMs)

    const onChange = () => {
      if (done) return
      if (!navigator.serviceWorker.controller) return
      done = true
      window.clearTimeout(timer)
      navigator.serviceWorker.removeEventListener('controllerchange', onChange)
      resolve(navigator.serviceWorker.controller)
    }

    navigator.serviceWorker.addEventListener('controllerchange', onChange)
  })
}

export async function mbSwSetPasteContext(params: {
  pasteId: string
  encryptionKey: Uint8Array
  accessKey?: string | null
  adminKey?: string | null
}): Promise<boolean> {
  if (!('serviceWorker' in navigator)) return false

  await registerMbServiceWorker()

  try {
    // Ensure the worker is active.
    await navigator.serviceWorker.ready
  } catch {
    // ignore
  }

  const controller = await waitForController()
  if (!controller) return false

  const msg: MbSwSetContextMessage = {
    type: 'mb:set-context',
    pasteId: params.pasteId,
    encryptionKeyBytes: Array.from(params.encryptionKey),
    accessKey: params.accessKey?.trim() ? params.accessKey.trim() : null,
    adminKey: params.adminKey?.trim() ? params.adminKey.trim() : null
  }

  const channel = new MessageChannel()
  const ackPromise = new Promise<boolean>((resolve) => {
    let done = false
    const timer = window.setTimeout(() => {
      if (done) return
      done = true
      resolve(false)
    }, 3000)

    channel.port1.onmessage = (e) => {
      if (done) return
      done = true
      window.clearTimeout(timer)
      const ok = Boolean((e.data as { ok?: unknown } | null | undefined)?.ok)
      resolve(ok)
    }
  })

  controller.postMessage(msg, [channel.port2])
  const ok = await ackPromise
  try {
    channel.port1.close()
  } catch {
    // ignore
  }
  return ok
}
