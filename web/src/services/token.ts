export const AUTH_TOKEN_EVENT = 'mb:auth-token'

const AUTH_SESSION_MARKER_KEY = 'mb:islogin'

let inMemoryAccessToken: string | null = null

function writeAuthSessionMarker(): void {
  try {
    window.localStorage.setItem(AUTH_SESSION_MARKER_KEY, 'true')
  } catch {
    // ignore
  }
}

function clearAuthSessionMarker(): void {
  try {
    window.localStorage.removeItem(AUTH_SESSION_MARKER_KEY)
  } catch {
    // ignore
  }
}

function emitTokenChanged(token: string | null): void {
  try {
    window.dispatchEvent(new CustomEvent(AUTH_TOKEN_EVENT, { detail: { token } }))
  } catch {
    // ignore
  }
}

export function saveAccessToken(token: string): void {
  inMemoryAccessToken = token
  writeAuthSessionMarker()
  emitTokenChanged(token)
}

export function loadAccessToken(): string | null {
  return inMemoryAccessToken
}

export function hasKnownAuthSession(): boolean {
  if (inMemoryAccessToken) return true
  try {
    return window.localStorage.getItem(AUTH_SESSION_MARKER_KEY) === 'true'
  } catch {
    return false
  }
}

export function clearAccessToken(): void {
  inMemoryAccessToken = null
  clearAuthSessionMarker()
  emitTokenChanged(null)
}
