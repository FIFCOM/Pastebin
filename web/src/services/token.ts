export const AUTH_TOKEN_EVENT = 'mb:auth-token'

let inMemoryAccessToken: string | null = null

function emitTokenChanged(token: string | null): void {
  try {
    window.dispatchEvent(new CustomEvent(AUTH_TOKEN_EVENT, { detail: { token } }))
  } catch {
    // ignore
  }
}

export function saveAccessToken(token: string): void {
  inMemoryAccessToken = token
  emitTokenChanged(token)
}

export function loadAccessToken(): string | null {
  return inMemoryAccessToken
}

export function clearAccessToken(): void {
  inMemoryAccessToken = null
  emitTokenChanged(null)
}
