import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosInstance,
  type InternalAxiosRequestConfig
} from 'axios'
import { clearAccessToken, loadAccessToken, saveAccessToken } from './token'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

type InstallAwareClientOptions = {
  withCredentials?: boolean
}

export function createInstallAwareHttpClient(options: InstallAwareClientOptions = {}): AxiosInstance {
  const client = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: options.withCredentials ?? false
  })
  attachInstallRequiredInterceptor(client)
  return client
}

export const authHttp = createInstallAwareHttpClient({ withCredentials: true })

export const apiHttp = createInstallAwareHttpClient({ withCredentials: true })

const INSTALL_REQUIRED_CODE = 'INSTALL_REQUIRED'
const INSTALL_ROUTE_PATH = (() => {
  const baseUrl = String(import.meta.env.BASE_URL || '/')
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl
  return `${normalizedBase}/install`.replace('//install', '/install')
})()
let installRedirecting = false

// Preemptively refresh to reduce near-expiry 401 "jitter" (default: 5 minutes).
// Can be overridden via Vite env: VITE_ACCESS_TOKEN_REFRESH_THRESHOLD_SECONDS.
const ACCESS_TOKEN_REFRESH_THRESHOLD_SECONDS = (() => {
  const raw = import.meta.env.VITE_ACCESS_TOKEN_REFRESH_THRESHOLD_SECONDS as string | undefined
  if (!raw) return 5 * 60
  const parsed = Number.parseInt(raw, 10)
  if (!Number.isFinite(parsed) || parsed < 0) return 5 * 60
  return parsed
})()

function base64UrlDecode(input: string): string {
  const normalized = input.replace(/-/g, '+').replace(/_/g, '/')
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=')
  return atob(padded)
}

function getTokenExp(token: string): number | null {
  const parts = token.split('.')
  if (parts.length !== 3) return null
  try {
    const payloadPart = parts[1]
    if (!payloadPart) return null
    const payloadJson = base64UrlDecode(payloadPart)
    const payload: unknown = JSON.parse(payloadJson)
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null
    const exp = (payload as { exp?: unknown }).exp
    if (typeof exp !== 'number' || !Number.isFinite(exp) || !Number.isSafeInteger(exp) || exp <= 0)
      return null
    return exp
  } catch {
    return null
  }
}

function isTokenExpiringSoon(token: string, thresholdSeconds: number): boolean {
  const exp = getTokenExp(token)
  if (!exp) return false
  const nowSeconds = Math.floor(Date.now() / 1000)
  return exp - nowSeconds <= thresholdSeconds
}

let refreshInFlight: Promise<string> | null = null

function isAuthDenied(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false
  const status = error.response?.status
  return status === 401 || status === 403
}

function isInstallRequiredError(error: AxiosError): boolean {
  if (error.response?.status !== 428) return false
  const data = error.response.data as { code?: unknown } | undefined
  return data?.code === INSTALL_REQUIRED_CODE
}

function redirectToInstallIfNeeded(): void {
  if (typeof window === 'undefined') return
  const path = window.location.pathname
  if (path === INSTALL_ROUTE_PATH || path === `${INSTALL_ROUTE_PATH}/`) return
  if (installRedirecting) return
  installRedirecting = true
  window.location.replace(INSTALL_ROUTE_PATH)
}

export async function refreshAccessToken(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = authHttp
      .post('/users/refresh')
      .then((resp) => {
        const newToken = (resp.data as { access_token: string }).access_token
        saveAccessToken(newToken)
        return newToken
      })
      .catch((err) => {
        // Only clear local auth state when refresh is denied (session revoked/expired).
        // Network errors should not force a logout.
        if (isAuthDenied(err)) {
          clearAccessToken()
        }
        throw err
      })
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

function isAuthEndpoint(url: string | undefined): boolean {
  if (!url) return false
  return (
    url.includes('/users/login') ||
    url.includes('/users/login-totp') ||
    url.includes('/users/register') ||
    url.includes('/users/refresh') ||
    url.includes('/users/logout')
  )
}

type RetryableAxiosConfig = InternalAxiosRequestConfig & { _retry?: boolean }

function ensureAxiosHeaders(
  headers: InternalAxiosRequestConfig['headers'] | undefined
): AxiosHeaders {
  if (!headers) return new AxiosHeaders()
  return headers instanceof AxiosHeaders ? headers : AxiosHeaders.from(headers)
}

export function attachInstallRequiredInterceptor(client: AxiosInstance): void {
  client.interceptors.response.use(
    (resp) => resp,
    (error: AxiosError) => {
      if (isInstallRequiredError(error)) {
        redirectToInstallIfNeeded()
      }
      return Promise.reject(error)
    }
  )
}

apiHttp.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  if (isAuthEndpoint(config.url)) {
    return config
  }

  const token = loadAccessToken()
  if (!token) return config

  const headers = ensureAxiosHeaders(config.headers)
  if (!headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)

  // 若即将过期，提前续期，避免出现“刚过期就 401”的抖动
  if (isTokenExpiringSoon(token, ACCESS_TOKEN_REFRESH_THRESHOLD_SECONDS)) {
    try {
      const newToken = await refreshAccessToken()
      headers.set('Authorization', `Bearer ${newToken}`)
    } catch (err) {
      if (isAuthDenied(err)) {
        clearAccessToken()
        // refresh 已被拒绝，不再携带旧 token 发请求
        headers.delete('Authorization')
        config.headers = headers
        throw err
      }
      // network / 5xx: keep current token and let request proceed
    }
  }

  config.headers = headers
  return config
})

apiHttp.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    if (isInstallRequiredError(error)) {
      redirectToInstallIfNeeded()
      return Promise.reject(error)
    }

    const status = error.response?.status
    const config = error.config as RetryableAxiosConfig | undefined

    if (status !== 401 || !config || config._retry || isAuthEndpoint(config.url)) {
      return Promise.reject(error)
    }

    const headers = ensureAxiosHeaders(config.headers)
    const reqAuth = headers.get('Authorization')
    const reqAuthStr = typeof reqAuth === 'string' ? reqAuth : undefined

    // API Key / 其它 bearer token：不尝试 refresh
    if (reqAuthStr?.startsWith('Bearer pk_')) {
      return Promise.reject(error)
    }

    config._retry = true

    try {
      const token = loadAccessToken()
      // 1) 如果请求携带了当前 access token，说明 token 过期/失效：刷新并重试
      // 2) 如果请求没带 token（比如刷新 cookie 仍有效、但内存 token 丢失），也尝试刷新并重试一次
      if (token && reqAuthStr && reqAuthStr !== `Bearer ${token}`) {
        return Promise.reject(error)
      }

      const newToken = await refreshAccessToken()
      const retryHeaders = ensureAxiosHeaders(config.headers)
      retryHeaders.set('Authorization', `Bearer ${newToken}`)
      config.headers = retryHeaders
      return apiHttp.request(config)
    } catch (refreshErr) {
      if (isAuthDenied(refreshErr)) {
        clearAccessToken()
        return Promise.reject(refreshErr)
      }
      // 网络/服务错误：返回原始 401，让调用方决定如何处理
      return Promise.reject(error)
    }
  }
)
