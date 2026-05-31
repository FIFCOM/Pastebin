import { computed, ref } from 'vue'
import type {
  FavoriteDetail,
  FavoriteListItem,
  ImportGuestFavoriteItem
} from '../services/favorites'
import {
  deleteFavorite,
  getFavoriteDetail,
  getFavorites,
  importGuestFavorites,
  saveFavorite
} from '../services/favorites'

const GUEST_FAVORITES_KEY = 'mb_favorites_guest_v1'

function userFavoritesKey(userId: number): string {
  return `mb_favorites_user_${userId}_v1`
}

export interface LocalGuestFavoriteItem {
  pasteId: string
  encryptionKey: string
  title?: string | null
  status?: 'published' | 'edited'
  localCreatedAt: number
  isDeleted: boolean
  isGuest: true
}

type FavoriteMeta = {
  title?: string | null
  status?: 'published' | 'edited'
  accessKey?: string
}

function loadTransientAccessKey(pasteId: string): string | undefined {
  if (typeof window === 'undefined') return undefined

  try {
    const value = sessionStorage.getItem(`mb_access_key:${pasteId}`)?.trim()
    return value || undefined
  } catch {
    return undefined
  }
}

export function loadGuestFavorites(): LocalGuestFavoriteItem[] {
  if (typeof window === 'undefined') return []

  try {
    const raw = localStorage.getItem(GUEST_FAVORITES_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []

    return parsed.flatMap((item): LocalGuestFavoriteItem[] => {
      if (!item || typeof item !== 'object') return []
      const entry = item as Partial<LocalGuestFavoriteItem>
      const pasteId = typeof entry.pasteId === 'string' ? entry.pasteId.trim() : ''
      const encryptionKey = typeof entry.encryptionKey === 'string' ? entry.encryptionKey.trim() : ''
      if (!pasteId || !encryptionKey) return []

      const localCreatedAt =
        typeof entry.localCreatedAt === 'number' && Number.isFinite(entry.localCreatedAt)
          ? entry.localCreatedAt
          : Date.now()

      return [{
        pasteId,
        encryptionKey,
        title: typeof entry.title === 'string' && entry.title.trim() ? entry.title.trim() : null,
        status: entry.status === 'edited' ? 'edited' : 'published',
        localCreatedAt,
        isDeleted: Boolean(entry.isDeleted),
        isGuest: true
      }]
    })
  } catch {
    return []
  }
}

function saveGuestFavorites(items: LocalGuestFavoriteItem[]): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(GUEST_FAVORITES_KEY, JSON.stringify(items))
}

export function clearGuestFavorites(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(GUEST_FAVORITES_KEY)
}

function removeGuestFavoriteItems(pasteIds: string[]): void {
  if (pasteIds.length === 0) return
  const set = new Set(pasteIds)
  saveGuestFavorites(loadGuestFavorites().filter((item) => !set.has(item.pasteId)))
}

function addGuestFavoriteItem(pasteId: string, encryptionKey: string, meta?: FavoriteMeta): void {
  const items = loadGuestFavorites()
  const idx = items.findIndex((item) => item.pasteId === pasteId)
  const normalizedTitle = typeof meta?.title === 'string' ? meta.title.trim() : ''
  const item: LocalGuestFavoriteItem = {
    pasteId,
    encryptionKey,
    title: normalizedTitle || null,
    status: meta?.status === 'edited' ? 'edited' : 'published',
    localCreatedAt: Date.now(),
    isDeleted: false,
    isGuest: true
  }

  if (idx >= 0) {
    items[idx] = item
  } else {
    items.unshift(item)
  }
  saveGuestFavorites(items)
}

function removeGuestFavoriteItem(pasteId: string): void {
  saveGuestFavorites(loadGuestFavorites().filter((item) => item.pasteId !== pasteId))
}

function guestCreatedAt(item: LocalGuestFavoriteItem): number {
  return typeof item.localCreatedAt === 'number' && Number.isFinite(item.localCreatedAt)
    ? item.localCreatedAt
    : 0
}

function toGuestFavoriteListItem(item: LocalGuestFavoriteItem): FavoriteListItem {
  const createdAt = guestCreatedAt(item) || Date.now()
  const iso = new Date(createdAt).toISOString()
  const title = typeof item.title === 'string' ? item.title.trim() : ''

  return {
    paste_id: item.pasteId,
    status: item.status === 'edited' ? 'edited' : 'published',
    title: title || null,
    max_views: -1,
    view_count: 0,
    published_at: null,
    paste_updated_at: iso,
    favorite_updated_at: iso,
    expire_at: null
  }
}

function loadUserFavoritesCache(userId: number): FavoriteListItem[] {
  if (typeof window === 'undefined') return []

  try {
    const raw = localStorage.getItem(userFavoritesKey(userId))
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    return Array.isArray(parsed) ? (parsed as FavoriteListItem[]) : []
  } catch {
    return []
  }
}

function saveUserFavoritesCache(userId: number, items: FavoriteListItem[]): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(userFavoritesKey(userId), JSON.stringify(items))
}

export function clearUserFavoritesCache(userId: number): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(userFavoritesKey(userId))
}

const favoriteItems = ref<FavoriteListItem[]>([])
const favoriteTotal = ref(0)
const favoritePage = ref(1)
const favoriteLimit = ref(20)
const favoriteLoading = ref(false)
const favoriteSearch = ref('')
let latestFetchRequestId = 0
let latestImportRequestId = 0

export function resetFavoritesState(): void {
  latestFetchRequestId += 1
  latestImportRequestId += 1
  favoriteItems.value = []
  favoriteTotal.value = 0
  favoritePage.value = 1
  favoriteLoading.value = false
  favoriteSearch.value = ''
}

function listItemFromDetail(detail: FavoriteDetail): FavoriteListItem {
  return {
    paste_id: detail.paste_id,
    status: detail.status,
    title: detail.title,
    max_views: detail.max_views,
    view_count: detail.view_count,
    published_at: detail.published_at,
    paste_updated_at: detail.paste_updated_at,
    favorite_updated_at: detail.favorite_updated_at,
    expire_at: detail.expire_at
  }
}

function cacheFavoriteItem(userId: number, item: FavoriteListItem): void {
  const cached = loadUserFavoritesCache(userId).filter((entry) => entry.paste_id !== item.paste_id)
  saveUserFavoritesCache(userId, [item, ...cached])
}

export function useFavorites() {
  const hasMore = computed(
    () => favoritePage.value * favoriteLimit.value < favoriteTotal.value
  )

  async function fetchFavorites(opts: {
    page?: number
    reset?: boolean
    search?: string
  } = {}, userId?: number | null): Promise<boolean> {
    const requestId = ++latestFetchRequestId
    const requestedPage = opts.page ?? (opts.reset ? 1 : favoritePage.value)

    if (opts.reset) {
      favoriteItems.value = []
      favoritePage.value = 1
    }
    if (opts.search !== undefined) favoriteSearch.value = opts.search

    favoriteLoading.value = true
    try {
      if (userId == null) {
        const keyword = favoriteSearch.value.trim().toLowerCase()
        const guestItems = loadGuestFavorites()
          .filter((item) => !item.isDeleted)
          .filter((item) => {
            if (!keyword) return true
            const title = typeof item.title === 'string' ? item.title.trim().toLowerCase() : ''
            return title.includes(keyword)
          })
          .sort((a, b) => guestCreatedAt(b) - guestCreatedAt(a))
          .map(toGuestFavoriteListItem)

        const total = guestItems.length
        const totalPages = Math.max(1, Math.ceil(total / favoriteLimit.value))
        const safePage = Math.min(Math.max(requestedPage, 1), totalPages)
        if (requestId !== latestFetchRequestId) return false
        const start = (safePage - 1) * favoriteLimit.value
        favoriteItems.value = guestItems.slice(start, start + favoriteLimit.value)
        favoriteTotal.value = total
        favoritePage.value = safePage
        return true
      }

      const params = {
        page: requestedPage,
        limit: favoriteLimit.value,
        ...(favoriteSearch.value ? { search: favoriteSearch.value } : {})
      }

      let resp = await getFavorites(params)
      if (requestId !== latestFetchRequestId) return false
      const totalPages = Math.max(1, Math.ceil(resp.total / favoriteLimit.value))
      const safePage = Math.min(Math.max(requestedPage, 1), totalPages)

      if (safePage !== requestedPage && resp.total > 0) {
        resp = await getFavorites({ ...params, page: safePage })
        if (requestId !== latestFetchRequestId) return false
      }

      favoriteItems.value = resp.items
      favoriteTotal.value = resp.total
      favoritePage.value = safePage
      if (!favoriteSearch.value && favoritePage.value === 1) {
        saveUserFavoritesCache(userId, favoriteItems.value)
      }
      return true
    } finally {
      if (requestId === latestFetchRequestId) {
        favoriteLoading.value = false
      }
    }
  }

  async function addFavorite(
    pasteId: string,
    encryptionKey: string,
    userId: number | null,
    meta?: FavoriteMeta
  ): Promise<void> {
    const normalizedPasteId = pasteId.trim()
    const normalizedKey = encryptionKey.trim()
    if (!normalizedPasteId || !normalizedKey) {
      throw new Error('缺少收藏所需的 Paste ID 或解密密钥')
    }

    if (userId == null) {
      addGuestFavoriteItem(normalizedPasteId, normalizedKey, meta)
      await fetchFavorites({ page: favoritePage.value }, null)
      return
    }

    const accessKey = meta?.accessKey?.trim()
    const detail = await saveFavorite(normalizedPasteId, normalizedKey, accessKey || undefined)
    const listItem = listItemFromDetail(detail)
    const idx = favoriteItems.value.findIndex((item) => item.paste_id === normalizedPasteId)
    if (idx >= 0) {
      favoriteItems.value[idx] = listItem
    } else {
      favoriteItems.value.unshift(listItem)
      favoriteTotal.value += 1
    }
    cacheFavoriteItem(userId, listItem)
  }

  async function removeFavorite(pasteId: string, userId: number | null): Promise<void> {
    if (userId == null) {
      removeGuestFavoriteItem(pasteId)
    } else {
      await deleteFavorite(pasteId)
    }

    favoriteItems.value = favoriteItems.value.filter((item) => item.paste_id !== pasteId)
    favoriteTotal.value = Math.max(0, favoriteTotal.value - 1)
    if (userId != null) {
      saveUserFavoritesCache(
        userId,
        loadUserFavoritesCache(userId).filter((item) => item.paste_id !== pasteId)
      )
    }
  }

  async function isFavorite(pasteId: string, userId: number | null): Promise<boolean> {
    const normalizedPasteId = pasteId.trim()
    if (!normalizedPasteId) return false

    if (userId == null) {
      return loadGuestFavorites().some((item) => item.pasteId === normalizedPasteId && !item.isDeleted)
    }

    if (favoriteItems.value.some((item) => item.paste_id === normalizedPasteId)) return true
    if (loadUserFavoritesCache(userId).some((item) => item.paste_id === normalizedPasteId)) return true

    try {
      const detail = await getFavoriteDetail(normalizedPasteId)
      const listItem = listItemFromDetail(detail)
      cacheFavoriteItem(userId, listItem)
      return true
    } catch {
      return false
    }
  }

  async function getFavoriteEncryptionKey(pasteId: string, userId: number | null): Promise<string | null> {
    const normalizedPasteId = pasteId.trim()
    if (!normalizedPasteId) return null

    if (userId == null) {
      const item = loadGuestFavorites().find((entry) => entry.pasteId === normalizedPasteId && !entry.isDeleted)
      return item?.encryptionKey || null
    }

    try {
      const detail = await getFavoriteDetail(normalizedPasteId)
      cacheFavoriteItem(userId, listItemFromDetail(detail))
      return detail.encryption_key || null
    } catch {
      return null
    }
  }

  async function importGuestFavoritesAndSync(userId: number): Promise<void> {
    const requestId = ++latestImportRequestId
    const guestItems = loadGuestFavorites().filter((item) => !item.isDeleted)
    if (guestItems.length === 0) {
      clearGuestFavorites()
      return
    }

    const importItems: ImportGuestFavoriteItem[] = guestItems.map((item) => {
      const accessKey = loadTransientAccessKey(item.pasteId)
      return {
        paste_id: item.pasteId,
        encryption_key: item.encryptionKey,
        ...(accessKey ? { access_key: accessKey } : {})
      }
    })

    try {
      const resp = await importGuestFavorites(importItems)
      if (requestId !== latestImportRequestId) return

      favoriteItems.value = resp.snapshot.items
      favoriteTotal.value = resp.snapshot.total
      favoritePage.value = 1
      favoriteSearch.value = ''
      saveUserFavoritesCache(userId, resp.snapshot.items)
      removeGuestFavoriteItems(resp.imported_ids)
      if (loadGuestFavorites().length === 0) {
        clearGuestFavorites()
      }
    } catch (e) {
      if (requestId !== latestImportRequestId) return
      console.error('导入游客收藏失败:', e)
    }
  }

  function initFavoritesFromCache(userId: number): void {
    const cached = loadUserFavoritesCache(userId)
    favoriteItems.value = cached
    favoriteTotal.value = cached.length
    favoritePage.value = 1
  }

  return {
    favoriteItems,
    favoriteTotal,
    favoritePage,
    favoriteLimit,
    favoriteLoading,
    favoriteSearch,
    items: favoriteItems,
    total: favoriteTotal,
    page: favoritePage,
    limit: favoriteLimit,
    loading: favoriteLoading,
    search: favoriteSearch,
    hasMore,
    fetchFavorites,
    addFavorite,
    removeFavorite,
    isFavorite,
    getFavoriteEncryptionKey,
    importGuestFavoritesAndSync,
    initFavoritesFromCache,
    clearUserFavoritesCache,
    resetFavoritesState
  }
}
