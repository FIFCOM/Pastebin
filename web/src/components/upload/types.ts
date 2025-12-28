export interface UploadingFile {
  id: string
  name: string
  size: number
  progress: number
  speed: number // bytes per second
  state: 'queued' | 'uploading'
  file: File
  uploadId?: string
  abortController?: AbortController
  fingerprint?: string
}

export interface UploadedFile {
  id: string
  fileId: string
  name: string
  size: number
  storedSize: number
  lastModified: number
  fingerprint: string
}

export interface FailedFile {
  id: string
  name: string
  size: number
  error: string
  file: File
  uploadId?: string
  fingerprint?: string
}

