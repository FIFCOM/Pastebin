import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
})

export interface PasteFile {
  id: string
  size: number
  encrypted_name: string
  url: string
}

export interface PasteData {
  title: string
  type: 'txt' | 'md'
  status: 'published' | 'edited'
  files: PasteFile[]
  published_at: string
  updated_at: string
  expire_at: string
}

export interface PasteContent {
  encrypted_content: string
}

export interface CreatePasteResponse {
  paste_id: string
  admin_key: string
  expire_at: string
}

export interface PublishSettings {
  title: string
  type: 'txt' | 'md'
  expire_time: '7d' | '30d' | '1y' | 'never'
  max_views: number
  access_key?: string
}

export interface PublishResponse {
  paste_id: string
  admin_key: string
  encryption_key?: string
}

export async function createPaste(encryptionMode: 'client' | 'server' = 'client'): Promise<CreatePasteResponse> {
  const response = await apiClient.post('/pastes', {
    encryption_mode: encryptionMode
  })
  return response.data
}

export async function uploadPasteContent(
  pasteId: string,
  adminKey: string,
  body: { encrypted_content?: string; content?: string }
): Promise<void> {
  await apiClient.post(
    `/pastes/${pasteId}/content`,
    body,
    {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminKey}`
      }
    }
  )
}

export async function publishPaste(
  pasteId: string,
  adminKey: string,
  settings: PublishSettings
): Promise<PublishResponse> {
  const response = await apiClient.post(
    `/pastes/${pasteId}/publish`,
    {
      settings
    },
    {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminKey}`
      }
    }
  )
  return response.data
}

export async function getPaste(pasteId: string, accessKey?: string): Promise<PasteData> {
  const response = await apiClient.get(`/pastes/${pasteId}`, {
    params: accessKey ? { access_key: accessKey } : undefined
  })
  return response.data
}

export async function getPasteContent(pasteId: string, accessKey?: string): Promise<PasteContent> {
  const response = await apiClient.get(`/pastes/${pasteId}/content`, {
    params: accessKey ? { access_key: accessKey } : undefined
  })
  return response.data
}