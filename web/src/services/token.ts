const LEGACY_ACCESS_TOKEN_STORAGE_KEY = 'mb_access_token'

export const AUTH_TOKEN_EVENT = 'mb:auth-token'

let inMemoryAccessToken: string | null = null

function emitTokenChanged(token: string | null): void {
  try {
    window.dispatchEvent(new CustomEvent(AUTH_TOKEN_EVENT, { detail: { token } }))
  } catch {
    // ignore
  }
}

function clearLegacyLocalStorageToken(): void {
  try {
    localStorage.removeItem(LEGACY_ACCESS_TOKEN_STORAGE_KEY)
  } catch {
    // ignore
  }
}

clearLegacyLocalStorageToken()

export function saveAccessToken(token: string): void {
  inMemoryAccessToken = token
  clearLegacyLocalStorageToken()
  emitTokenChanged(token)
}

export function loadAccessToken(): string | null {
  clearLegacyLocalStorageToken()
  return inMemoryAccessToken
}

export function clearAccessToken(): void {
  inMemoryAccessToken = null
  clearLegacyLocalStorageToken()
  emitTokenChanged(null)
}
