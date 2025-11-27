import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
})

export interface UserResponse {
  id: number
  username: string
  email: string | null
  totp_enabled: boolean
  created_at: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

const TOKEN_STORAGE_KEY = 'mb_access_token'

export async function sha256Hex(plain: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(plain)
  const digest = await crypto.subtle.digest('SHA-256', data)
  const bytes = new Uint8Array(digest)
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

export function saveToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } catch (e) {
    console.error('Failed to save token to localStorage', e)
  }
}

export function loadToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch (e) {
    console.error('Failed to load token from localStorage', e)
    return null
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch (e) {
    console.error('Failed to clear token from localStorage', e)
  }
}

export async function registerUser(email: string, password: string): Promise<UserResponse> {
  const passwordHash = await sha256Hex(password)
  const response = await apiClient.post('/users/register', {
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
  const response = await apiClient.post('/users/login', {
    email,
    password: passwordHash
  })
  return response.data
}

export async function fetchCurrentUser(token: string): Promise<UserResponse> {
  const response = await apiClient.get('/users/me', {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
  return response.data
}