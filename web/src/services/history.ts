import { apiHttp } from './http'

export interface HistoryListItem {
  paste_id: string
  status: string
  title: string | null
  max_views: number
  view_count: number
  published_at: string | null
  paste_updated_at: string
  history_updated_at: string
  expire_at: string | null
}

export interface HistoryDetail extends HistoryListItem {
  admin_key: string
  encryption_key: string
}

export interface HistoryListResponse {
  items: HistoryListItem[]
  total: number
  page: number
  limit: number
}

export interface ImportGuestItem {
  paste_id: string
  admin_key: string
  encryption_key: string
}

export interface ImportGuestResponse {
  imported: number
  imported_ids: string[]
  skipped: number
  errors: string[]
  snapshot: HistoryListResponse
}

export interface HistoryListParams {
  page?: number
  limit?: number
  search?: string
}

export async function getHistory(params: HistoryListParams = {}): Promise<HistoryListResponse> {
  const response = await apiHttp.get('/user/history', { params })
  return response.data
}

export async function getHistoryDetail(pasteId: string): Promise<HistoryDetail> {
  const response = await apiHttp.get(`/user/history/${pasteId}`)
  return response.data
}

export async function saveToHistory(
  pasteId: string,
  adminKey: string,
  encryptionKey: string
): Promise<HistoryDetail> {
  const response = await apiHttp.post(`/user/history/${pasteId}`, {
    admin_key: adminKey,
    encryption_key: encryptionKey
  })
  return response.data
}

export async function deleteHistory(pasteId: string): Promise<void> {
  await apiHttp.delete(`/user/history/${pasteId}`)
}

export async function importGuestHistory(items: ImportGuestItem[]): Promise<ImportGuestResponse> {
  const response = await apiHttp.post('/user/history/import_guest', { items })
  return response.data
}
