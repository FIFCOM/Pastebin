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

export interface UserCreateRequest {
  username?: string
  email: string
  password: string
}

export interface UserUpdateRequest {
  email?: string
  password?: string
}

export async function listUsers(page = 1, size = 10): Promise<UserListResponse> {
  const response = await apiHttp.get<UserListResponse>('/users', { params: { page, size } })
  return response.data
}

export async function createUser(user: UserCreateRequest): Promise<UserResponse> {
  const passwordHash = await sha256Hex(user.password)
  const body: { username?: string; email: string; password: string } = {
    email: user.email.trim(),
    password: passwordHash
  }

  const username = user.username?.trim()
  if (username) body.username = username

  const response = await apiHttp.post<UserResponse>('/users', body)
  return response.data
}

export async function updateUser(userId: number, update: UserUpdateRequest): Promise<UserResponse> {
  const body: { email?: string; password?: string } = {}
  const email = update.email?.trim()
  if (email) body.email = email
  if (update.password) {
    body.password = await sha256Hex(update.password)
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
}

export async function getUserSessions(userId: number): Promise<SessionResponse[]> {
  const response = await apiHttp.get<SessionResponse[]>(`/users/${userId}/sessions`)
  return response.data
}

export async function revokeSession(sessionId: string): Promise<MessageResponse> {
  const response = await apiHttp.delete<MessageResponse>(`/users/sessions/${sessionId}`)
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
  qr_code_url: string
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
  created_at: string
}

export interface ApiKeyCreateResponse {
  id: number
  name: string
  api_key: string
  created_at: string
}

export interface ApiKeyListResponse {
  api_keys: ApiKeyResponse[]
}

export async function listApiKeys(): Promise<ApiKeyListResponse> {
  const response = await apiHttp.get<ApiKeyListResponse>('/user/apikeys')
  return response.data
}

export async function createApiKey(name: string): Promise<ApiKeyCreateResponse> {
  const response = await apiHttp.post<ApiKeyCreateResponse>('/user/apikeys', {
    name: name.trim()
  })
  return response.data
}

export async function deleteApiKey(keyId: number): Promise<MessageResponse> {
  const response = await apiHttp.delete<MessageResponse>(`/user/apikeys/${keyId}`)
  return response.data
}
