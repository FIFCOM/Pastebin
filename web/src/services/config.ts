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

export async function getPublicConfig(): Promise<PublicConfig> {
  if (cachedConfig) {
    return cachedConfig
  }

  try {
    const response = await apiClient.get<PublicConfig>('/config')
    cachedConfig = response.data
    return cachedConfig
  } catch (error) {
    console.warn('Failed to fetch config, using defaults:', error)
    return DEFAULT_CONFIG
  }
}
