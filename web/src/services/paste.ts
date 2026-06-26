import { apiHttp, createInstallAwareHttpClient } from './http'

const apiClient = createInstallAwareHttpClient()

function adminKeyHeaders(adminKey: string) {
  return {
    'X-Paste-Admin-Key': adminKey
  }
}

export interface PasteFile {
  id: string
  size: number
  encrypted_name: string
  url: string
  plain_size?: number | null
}

export interface PasteData {
  title: string | null
  type: 'txt' | 'md'
  status: 'published' | 'edited' | 'draft'
  published_at: string | null
  updated_at: string
  expire_at: string | null
  view_count: number
  max_views: number
}

export interface PasteContent {
  encrypted_content?: string | null
  content?: string | null
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
  file_id?: string
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

export interface PasteUpdateRequest {
  title?: string
  type?: 'txt' | 'md'
  expire_time?: '7d' | '30d' | '1y' | 'never'
  max_views?: number
  access_key?: string | null
}

export interface CreatePasteOptions {
  authorization?: string
}

export async function createPaste(
  encryptionMode: 'client' | 'server' = 'client',
  options: CreatePasteOptions = {}
): Promise<CreatePasteResponse> {
  const response = await apiHttp.post('/pastes', {
    encryption_mode: encryptionMode
  }, {
    headers: options.authorization ? { Authorization: options.authorization } : undefined
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
        ...adminKeyHeaders(adminKey)
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
        ...adminKeyHeaders(adminKey)
      }
    }
  )
  return response.data
}

export async function updatePaste(
  pasteId: string,
  adminKey: string,
  update: PasteUpdateRequest
): Promise<void> {
  await apiClient.put(
    `/pastes/${pasteId}`,
    update,
    {
      headers: {
        'Content-Type': 'application/json',
        ...adminKeyHeaders(adminKey)
      }
    }
  )
}

export async function getPaste(
  pasteId: string,
  accessKey?: string,
  adminKey?: string
): Promise<PasteData> {
  const response = await apiClient.get(`/pastes/${pasteId}`, {
    params: accessKey ? { access_key: accessKey } : undefined,
    headers: adminKey
      ? adminKeyHeaders(adminKey)
      : undefined
  })
  return response.data
}

export async function getPasteContent(
  pasteId: string,
  accessKey?: string,
  adminKey?: string
): Promise<PasteContent> {
  const params: Record<string, string> = {}
  if (accessKey) params.access_key = accessKey

  const response = await apiClient.get(`/pastes/${pasteId}/content`, {
    params: Object.keys(params).length > 0 ? params : undefined,
    headers: adminKey
      ? adminKeyHeaders(adminKey)
      : undefined
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
      ...adminKeyHeaders(adminKey),
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
      ...adminKeyHeaders(adminKey)
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
      ...adminKeyHeaders(adminKey),
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
      ...adminKeyHeaders(adminKey)
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
      ...adminKeyHeaders(adminKey)
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
      ...adminKeyHeaders(adminKey)
    }
  })
}
