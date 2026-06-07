import { apiHttp } from './http'

export type CleanupTaskName =
  | 'expired_drafts'
  | 'expired_pastes'
  | 'expired_members'
  | 'expired_uploads'
  | 'expired_user_sessions'
  | 'expired_used_refresh_tokens'

export interface AdminOverviewResponse {
  total_users: number
  active_users: number
  total_pastes: number
  total_files: number
  total_storage_bytes: number
  total_view_count: number
  cleanup_counts: Record<CleanupTaskName, number>
}

export type AdminPasteStatus = 'draft' | 'published' | 'edited'
export type AdminPasteType = 'txt' | 'md'
export type AdminPasteEncryptionMode = 'client' | 'server'

export interface AdminPasteListItem {
  id: string
  title: string | null
  status: AdminPasteStatus
  type: AdminPasteType
  encryption_mode: AdminPasteEncryptionMode
  view_count: number
  max_views: number
  file_count: number
  file_total_size: number
  created_at: string
  updated_at: string
  published_at: string | null
  expire_at: string | null
}

export interface AdminPasteListResponse {
  pastes: AdminPasteListItem[]
  total: number
  page: number
  size: number
}

export interface ListAdminPastesOptions {
  page?: number
  size?: number
  search?: string
  status?: AdminPasteStatus
  type?: AdminPasteType
  encryptionMode?: AdminPasteEncryptionMode
}

export interface AdminCleanupStatusResponse {
  supported_tasks: CleanupTaskName[]
  cleanup_counts: Record<CleanupTaskName, number>
}

export interface CleanupTaskResult {
  task_name: CleanupTaskName | string
  success: boolean
  deleted_count: number
  message: string
  error: string | null
}

export interface CleanupResponse {
  success: boolean
  total_deleted: number
  task_results: CleanupTaskResult[]
  message: string
}

export interface MessageResponse {
  message: string
}

export async function getAdminOverview(): Promise<AdminOverviewResponse> {
  const response = await apiHttp.get<AdminOverviewResponse>('/users/admin/overview')
  return response.data
}

export async function listAdminPastes(options: ListAdminPastesOptions = {}): Promise<AdminPasteListResponse> {
  const params: {
    page: number
    size: number
    search?: string
    status?: AdminPasteStatus
    type?: AdminPasteType
    encryption_mode?: AdminPasteEncryptionMode
  } = {
    page: options.page ?? 1,
    size: options.size ?? 10
  }

  const search = options.search?.trim()
  if (search) params.search = search
  if (options.status) params.status = options.status
  if (options.type) params.type = options.type
  if (options.encryptionMode) params.encryption_mode = options.encryptionMode

  const response = await apiHttp.get<AdminPasteListResponse>('/users/admin/pastes', { params })
  return response.data
}

export async function deleteAdminPaste(pasteId: string): Promise<MessageResponse> {
  const response = await apiHttp.delete<MessageResponse>(`/users/admin/pastes/${encodeURIComponent(pasteId)}`)
  return response.data
}

export async function getAdminCleanupStatus(): Promise<AdminCleanupStatusResponse> {
  const response = await apiHttp.get<AdminCleanupStatusResponse>('/users/admin/cleanup')
  return response.data
}

export async function executeAdminCleanup(tasks: CleanupTaskName[]): Promise<CleanupResponse> {
  const response = await apiHttp.post<CleanupResponse>('/users/admin/cleanup', { tasks })
  return response.data
}
