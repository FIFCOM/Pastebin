import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
})

export interface PublicConfig {
  max_upload_file_size: number
  max_chunk_size: number
}

// 默认配置（后端不可用时的回退值）
const DEFAULT_CONFIG: PublicConfig = {
  max_upload_file_size: 10 * 1024 * 1024,
  max_chunk_size: 2 * 1024 * 1024
}

let cachedConfig: PublicConfig | null = null

const PUBLIC_CONFIG_STORAGE_KEY = 'mb_public_config'

function loadStoredConfig(): PublicConfig | null {
  try {
    const raw = localStorage.getItem(PUBLIC_CONFIG_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<PublicConfig> | null
    if (!parsed) return null

    const maxUpload = parsed.max_upload_file_size
    const maxChunk = parsed.max_chunk_size
    if (typeof maxUpload !== 'number' || !Number.isFinite(maxUpload) || maxUpload <= 0) return null
    if (typeof maxChunk !== 'number' || !Number.isFinite(maxChunk) || maxChunk <= 0) return null

    return { max_upload_file_size: maxUpload, max_chunk_size: maxChunk }
  } catch (e) {
    console.warn('Failed to load config from localStorage:', e)
    return null
  }
}

function saveStoredConfig(config: PublicConfig): void {
  try {
    localStorage.setItem(PUBLIC_CONFIG_STORAGE_KEY, JSON.stringify(config))
  } catch (e) {
    console.warn('Failed to save config to localStorage:', e)
  }
}

export async function getPublicConfig(): Promise<PublicConfig> {
  if (cachedConfig) {
    return cachedConfig
  }

  const stored = loadStoredConfig()
  if (stored) {
    cachedConfig = stored
    return cachedConfig
  }

  try {
    const response = await apiClient.get<PublicConfig>('/config')
    cachedConfig = response.data
    saveStoredConfig(cachedConfig)
    return cachedConfig
  } catch (error) {
    console.warn('Failed to fetch config, using defaults:', error)
    return DEFAULT_CONFIG
  }
}
