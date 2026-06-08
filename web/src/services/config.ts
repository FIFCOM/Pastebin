import { createInstallAwareHttpClient } from './http'

const apiClient = createInstallAwareHttpClient()

export interface PublicConfig {
  max_upload_file_size: number
  max_chunk_size: number
  email_verification_enabled: boolean
}

// 前端本地配置：多文件上传并发数
export const DEFAULT_UPLOAD_CONCURRENCY = 10
// 默认配置（后端不可用时的回退值）
const DEFAULT_CONFIG: PublicConfig = {
  max_upload_file_size: 10 * 1024 * 1024,
  max_chunk_size: 2 * 1024 * 1024,
  email_verification_enabled: false
}

let cachedConfig: PublicConfig | null = null
let cachedConfigAt = 0

const PUBLIC_CONFIG_STORAGE_KEY = 'mb_public_config'
const PUBLIC_CONFIG_TTL_MS = 30_000

interface StoredPublicConfig {
  config: PublicConfig
  cached_at: number
}

function isFreshConfig(cachedAt: number): boolean {
  return Date.now() - cachedAt < PUBLIC_CONFIG_TTL_MS
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isPublicConfig(value: unknown): value is PublicConfig {
  if (!isRecord(value)) return false

  const maxUpload = value.max_upload_file_size
  const maxChunk = value.max_chunk_size
  const emailVerificationEnabled = value.email_verification_enabled

  return (
    typeof maxUpload === 'number' &&
    Number.isFinite(maxUpload) &&
    maxUpload > 0 &&
    typeof maxChunk === 'number' &&
    Number.isFinite(maxChunk) &&
    maxChunk > 0 &&
    typeof emailVerificationEnabled === 'boolean'
  )
}

function loadStoredConfig(): StoredPublicConfig | null {
  try {
    const raw = localStorage.getItem(PUBLIC_CONFIG_STORAGE_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!isRecord(parsed)) return null

    if ('config' in parsed) {
      const cachedAt = Number(parsed.cached_at ?? 0)
      return isPublicConfig(parsed.config) && Number.isFinite(cachedAt)
        ? { config: parsed.config, cached_at: cachedAt }
        : null
    }

    // 兼容旧格式缓存；让它立即过期，以便下一次从后端刷新。
    return isPublicConfig(parsed) ? { config: parsed, cached_at: 0 } : null
  } catch (e) {
    console.warn('Failed to load config from localStorage:', e)
    return null
  }
}

function saveStoredConfig(config: PublicConfig): void {
  try {
    localStorage.setItem(
      PUBLIC_CONFIG_STORAGE_KEY,
      JSON.stringify({
        config,
        cached_at: Date.now()
      })
    )
  } catch (e) {
    console.warn('Failed to save config to localStorage:', e)
  }
}

export async function getPublicConfig(): Promise<PublicConfig> {
  if (cachedConfig && isFreshConfig(cachedConfigAt)) {
    return cachedConfig
  }

  const stored = loadStoredConfig()
  if (stored && isFreshConfig(stored.cached_at)) {
    cachedConfig = stored.config
    cachedConfigAt = stored.cached_at
    return cachedConfig
  }

  try {
    const response = await apiClient.get<PublicConfig>('/config')
    cachedConfig = response.data
    cachedConfigAt = Date.now()
    saveStoredConfig(cachedConfig)
    return cachedConfig
  } catch (error) {
    console.warn('Failed to fetch config, using defaults:', error)
    if (stored) return stored.config
    return DEFAULT_CONFIG
  }
}

export function invalidatePublicConfigCache(): void {
  cachedConfig = null
  cachedConfigAt = 0
  try {
    localStorage.removeItem(PUBLIC_CONFIG_STORAGE_KEY)
  } catch (e) {
    console.warn('Failed to clear config from localStorage:', e)
  }
}
