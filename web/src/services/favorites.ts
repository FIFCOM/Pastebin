import { apiHttp } from './http'

export interface FavoriteListItem {
  paste_id: string
  status: string
  title: string | null
  max_views: number
  view_count: number
  published_at: string | null
  paste_updated_at: string
  favorite_updated_at: string
  expire_at: string | null
}

export interface FavoriteDetail extends FavoriteListItem {
  encryption_key: string
}

export interface FavoriteListResponse {
  items: FavoriteListItem[]
  total: number
  page: number
  limit: number
}

export interface ImportGuestFavoriteItem {
  paste_id: string
  encryption_key: string
  access_key?: string
}

export interface ImportGuestFavoritesResponse {
  imported: number
  imported_ids: string[]
  skipped: number
  errors: string[]
  snapshot: FavoriteListResponse
}

export interface FavoriteListParams {
  page?: number
  limit?: number
  search?: string
}

export async function getFavorites(params: FavoriteListParams = {}): Promise<FavoriteListResponse> {
  const response = await apiHttp.get('/user/favorites', { params })
  return response.data
}

export async function getFavoriteDetail(pasteId: string): Promise<FavoriteDetail> {
  const response = await apiHttp.get(`/user/favorites/${pasteId}`)
  return response.data
}

export async function saveFavorite(
  pasteId: string,
  encryptionKey: string,
  accessKey?: string
): Promise<FavoriteDetail> {
  const response = await apiHttp.put(`/user/favorites/${pasteId}`, {
    encryption_key: encryptionKey,
    ...(accessKey ? { access_key: accessKey } : {})
  })
  return response.data
}

export async function deleteFavorite(pasteId: string): Promise<void> {
  await apiHttp.delete(`/user/favorites/${pasteId}`)
}

export async function importGuestFavorites(
  items: ImportGuestFavoriteItem[]
): Promise<ImportGuestFavoritesResponse> {
  const response = await apiHttp.post('/user/favorites/import_guest', { items })
  return response.data
}
