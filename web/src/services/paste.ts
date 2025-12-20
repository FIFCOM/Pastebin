import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
})

export interface PasteFile {
  id: string
  size: number
  encrypted_name: string
  url: string
  plain_size?: number | null
}

export interface PasteData {
  title: string
  type: 'txt' | 'md'
  status: 'published' | 'edited'
  published_at: string
  updated_at: string
  expire_at: string
}

export interface PasteContent {
  encrypted_content: string
  files: PasteFile[]
}

export interface FileUploadInitRequest {
  encryption_mode?: 'client' | 'server'
  file_name: string
  mime_type?: string
  file_size: number
  requested_chunk_size?: number
}

export interface FileUploadInitResponse {
  upload_id: string
  chunk_size: number
  total_chunks: number
  expires_at: string
  max_total_upload_size: number
  remaining_upload_size: number | null
}

export interface FileUploadCompleteResponse {
  file_id: string
  max_total_upload_size: number
  remaining_upload_size: number | null
}

export interface FileUploadStatusResponse {
  upload_id: string
  encryption_mode: 'client' | 'server'
  file_size: number
  chunk_size: number
  total_chunks: number
  expires_at: string
  max_total_upload_size: number
  remaining_upload_size: number | null
  uploaded_chunks: number[]
  uploaded_count: number
  next_index: number
  completed: boolean
}

export interface CreatePasteResponse {
  paste_id: string
  admin_key: string
  expires_at: string
  max_total_upload_size: number
  remaining_upload_size: number | null
  timestamp: number
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

export async function initFileUpload(
  pasteId: string,
  adminKey: string,
  body: FileUploadInitRequest,
  encryptionKey?: string,
  signal?: AbortSignal
): Promise<FileUploadInitResponse> {
  const response = await apiClient.post(`/pastes/${pasteId}/files/init`, body, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${adminKey}`,
      ...(encryptionKey ? { 'X-Encryption-Key': encryptionKey } : {})
    },
    signal
  })
  return response.data
}

export async function uploadFileChunk(
  pasteId: string,
  adminKey: string,
  uploadId: string,
  index: number,
  chunk: ArrayBuffer | Uint8Array | Blob,
  onProgress?: (loaded: number, total: number) => void,
  signal?: AbortSignal
): Promise<void> {
  await apiClient.put(`/pastes/${pasteId}/files/${uploadId}/chunk/${index}`, chunk, {
    headers: {
      'Content-Type': 'application/octet-stream',
      Authorization: `Bearer ${adminKey}`
    },
    transformRequest: (d) => d,
    onUploadProgress: onProgress ? (e) => onProgress(e.loaded, e.total ?? 0) : undefined,
    signal
  })
}

export async function completeFileUpload(
  pasteId: string,
  adminKey: string,
  uploadId: string,
  body: { checksum_sha256?: string } = {},
  encryptionKey?: string,
  signal?: AbortSignal
): Promise<FileUploadCompleteResponse> {
  const response = await apiClient.post(`/pastes/${pasteId}/files/${uploadId}/complete`, body, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${adminKey}`,
      ...(encryptionKey ? { 'X-Encryption-Key': encryptionKey } : {})
    },
    signal
  })
  return response.data
}

export async function getFileUploadStatus(
  pasteId: string,
  adminKey: string,
  uploadId: string,
  signal?: AbortSignal
): Promise<FileUploadStatusResponse> {
  const response = await apiClient.get(`/pastes/${pasteId}/files/${uploadId}/status`, {
    headers: {
      Authorization: `Bearer ${adminKey}`
    },
    signal
  })
  return response.data
}

export async function abortFileUpload(
  pasteId: string,
  adminKey: string,
  uploadId: string
): Promise<void> {
  await apiClient.post(`/pastes/${pasteId}/files/${uploadId}/abort`, null, {
    headers: {
      Authorization: `Bearer ${adminKey}`
    }
  })
}

export async function deleteFile(
  pasteId: string,
  adminKey: string,
  fileId: string
): Promise<void> {
  await apiClient.delete(`/pastes/${pasteId}/files/${fileId}`, {
    headers: {
      Authorization: `Bearer ${adminKey}`
    }
  })
}
