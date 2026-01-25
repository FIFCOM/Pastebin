import { apiHttp, authHttp } from './http'

export interface UserResponse {
  id: number
  username: string
  email: string | null
  totp_enabled: boolean
  created_at: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: UserResponse
}

export async function sha256Hex(plain: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(plain)
  const digest = await crypto.subtle.digest('SHA-256', data)
  const bytes = new Uint8Array(digest)
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

export async function registerUser(email: string, password: string): Promise<UserResponse> {
  const passwordHash = await sha256Hex(password)
  const response = await authHttp.post('/users/register', {
    email,
    password: passwordHash
  })
  return response.data
}

export async function loginUser(
  email: string,
  password: string
): Promise<LoginResponse> {
  const passwordHash = await sha256Hex(password)
  const response = await authHttp.post('/users/login', {
    email,
    password: passwordHash
  })
  return response.data
}

export async function loginUserWithTotp(
  email: string,
  password: string,
  totpCode: string
): Promise<LoginResponse> {
  const passwordHash = await sha256Hex(password)
  const response = await authHttp.post('/users/login-totp', {
    email,
    password: passwordHash,
    totp_code: totpCode
  })
  return response.data
}

export async function fetchCurrentUser(): Promise<UserResponse> {
  const response = await apiHttp.get('/users/me')
  return response.data
}

export async function logoutSession(): Promise<void> {
  await authHttp.post('/users/logout')
}

export async function logoutAllSessions(): Promise<void> {
  await apiHttp.post('/users/logout-all')
}
