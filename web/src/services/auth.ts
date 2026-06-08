import { apiHttp, authHttp } from './http'

export interface UserResponse {
  id: number
  username: string
  email: string | null
  role: 'admin' | 'user'
  is_active: boolean
  totp_enabled: boolean
  email_verified_at: string | null
  created_at: string
}

export interface LoginResponse {
  access_token: string
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

export async function registerUser(
  email: string,
  password: string,
  verificationCode?: string
): Promise<UserResponse> {
  const passwordHash = await sha256Hex(password)
  const body: {
    email: string
    password: string
    verification_code?: string
  } = {
    email,
    password: passwordHash
  }
  const code = verificationCode?.trim()
  if (code) body.verification_code = code
  const response = await authHttp.post('/users/register', body)
  return response.data
}

export async function sendEmailVerificationCode(
  email: string,
  purpose: 'register' | 'reset_password'
): Promise<void> {
  await authHttp.post('/users/email-verification-codes', {
    email: email.trim(),
    purpose
  })
}

export async function resetPassword(
  email: string,
  password: string,
  verificationCode: string
): Promise<void> {
  const passwordHash = await sha256Hex(password)
  await authHttp.post('/users/password-reset', {
    email: email.trim(),
    password: passwordHash,
    verification_code: verificationCode.trim()
  })
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
