import { sha256Hex } from './auth'
import type { UserResponse } from './auth'
import { apiHttp } from './http'

export interface MessageResponse {
  message: string
}

export interface UserListResponse {
  users: UserResponse[]
  total: number
  page: number
  size: number
}

export interface ListUsersOptions {
  page?: number
  size?: number
  search?: string
  role?: 'admin' | 'user'
  isActive?: boolean
}

export interface UserCreateRequest {
  username?: string
  email: string
  password: string
  role?: 'admin' | 'user'
}

export interface UserUpdateRequest {
  username?: string
  email?: string
  password?: string
  current_password?: string
  role?: 'admin' | 'user'
  is_active?: boolean
}

export async function listUsers(options: ListUsersOptions = {}): Promise<UserListResponse> {
  const params: {
    page: number
    size: number
    search?: string
    role?: 'admin' | 'user'
    is_active?: boolean
  } = {
    page: options.page ?? 1,
    size: options.size ?? 10
  }

  const search = options.search?.trim()
  if (search) params.search = search
  if (options.role) params.role = options.role
  if (typeof options.isActive === 'boolean') params.is_active = options.isActive

  const response = await apiHttp.get<UserListResponse>('/users', { params })
  return response.data
}

export async function createUser(user: UserCreateRequest): Promise<UserResponse> {
  const passwordHash = await sha256Hex(user.password)
  const email = user.email.trim()
  if (!email) throw new Error('邮箱不能为空')

  const body: { username?: string; email: string; password: string; role?: 'admin' | 'user' } = {
    email,
    password: passwordHash
  }

  const username = user.username?.trim()
  if (username) body.username = username
  if (user.role) body.role = user.role

  const response = await apiHttp.post<UserResponse>('/users', body)
  return response.data
}

export async function updateUser(userId: number, update: UserUpdateRequest): Promise<UserResponse> {
  const body: {
    username?: string
    email?: string
    password?: string
    current_password?: string
    role?: 'admin' | 'user'
    is_active?: boolean
  } = {}

  const username = update.username?.trim()
  if (username) body.username = username

  if (update.email !== undefined) {
    const email = update.email.trim()
    if (!email) throw new Error('邮箱不能为空')
    body.email = email
  }

  if (update.password) {
    body.password = await sha256Hex(update.password)
  }

  if (update.current_password) {
    body.current_password = await sha256Hex(update.current_password)
  }

  if (update.role) {
    body.role = update.role
  }

  if (typeof update.is_active === 'boolean') {
    body.is_active = update.is_active
  }

  const response = await apiHttp.put<UserResponse>(`/users/${userId}`, body)
  return response.data
}

export async function deleteUser(userId: number): Promise<MessageResponse> {
  const response = await apiHttp.delete<MessageResponse>(`/users/${userId}`)
  return response.data
}

export interface SessionResponse {
  id: string
  user_id: number
  expires_at: string
  created_at: string
  user_agent: string | null
  ip_address: string | null
  last_active_at: string | null
  is_current: boolean
}

export async function getUserSessions(userId: number): Promise<SessionResponse[]> {
  const response = await apiHttp.get<SessionResponse[]>(`/users/${userId}/sessions`)
  return response.data
}

export async function revokeSession(sessionId: string): Promise<MessageResponse> {
  const response = await apiHttp.delete<MessageResponse>(`/users/sessions/${sessionId}`)
  return response.data
}

export async function revokeOtherSessions(userId: number): Promise<MessageResponse> {
  const response = await apiHttp.delete<MessageResponse>(`/users/${userId}/sessions/others`)
  return response.data
}

export async function cleanupExpiredSessions(): Promise<MessageResponse> {
  const response = await apiHttp.post<MessageResponse>('/users/cleanup-sessions')
  return response.data
}

export interface TotpStatusResponse {
  enabled: boolean
  setup_required: boolean
}

export interface TotpSetupResponse {
  secret: string
  provisioning_uri: string
}

export async function getTotpStatus(): Promise<TotpStatusResponse> {
  const response = await apiHttp.get<TotpStatusResponse>('/users/me/totp')
  return response.data
}

export async function setupTotp(): Promise<TotpSetupResponse> {
  const response = await apiHttp.post<TotpSetupResponse>('/users/me/totp')
  return response.data
}

export async function verifyTotp(totpCode: string): Promise<MessageResponse> {
  const response = await apiHttp.post<MessageResponse>('/users/me/totp/verify', {
    totp_code: totpCode
  })
  return response.data
}

export async function disableTotp(): Promise<MessageResponse> {
  const response = await apiHttp.delete<MessageResponse>('/users/me/totp')
  return response.data
}

export interface ApiKeyResponse {
  id: number
  name: string
  key_preview: string | null
  created_at: string
  last_used_at: string | null
  last_used_ip: string | null
  expires_at: string | null
}

export interface ApiKeyCreateResponse {
  id: number
  name: string
  api_key: string
  key_preview: string | null
  created_at: string
  last_used_at: string | null
  last_used_ip: string | null
  expires_at: string | null
}

export interface ApiKeyListResponse {
  api_keys: ApiKeyResponse[]
}

export async function listApiKeys(): Promise<ApiKeyListResponse> {
  const response = await apiHttp.get<ApiKeyListResponse>('/user/apikeys')
  return response.data
}

export async function createApiKey(
  name: string,
  options: { expiresInDays?: number | null } = {}
): Promise<ApiKeyCreateResponse> {
  const body: { name: string; expires_in_days?: number } = {
    name: name.trim()
  }

  const expiresInDays = options.expiresInDays
  if (typeof expiresInDays === 'number' && Number.isFinite(expiresInDays) && expiresInDays > 0) {
    body.expires_in_days = Math.floor(expiresInDays)
  }

  const response = await apiHttp.post<ApiKeyCreateResponse>('/user/apikeys', body)
  return response.data
}

export async function deleteApiKey(keyId: number): Promise<MessageResponse> {
  const response = await apiHttp.delete<MessageResponse>(`/user/apikeys/${keyId}`)
  return response.data
}

export async function cleanupExpiredApiKeys(): Promise<MessageResponse> {
  const response = await apiHttp.post<MessageResponse>('/user/apikeys/cleanup-expired')
  return response.data
}
