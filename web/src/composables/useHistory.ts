import { ref, computed } from 'vue'
import type { HistoryListItem, ImportGuestItem } from '../services/history'
import {
  getHistory,
  saveToHistory,
  starHistory,
  deleteHistory,
  importGuestHistory
} from '../services/history'

// ===========================
// 本地存储 key 约定
// ===========================
const GUEST_HISTORY_KEY = 'mb_history_guest_v1'

function userHistoryKey(userId: number): string {
  return `mb_history_user_${userId}_v1`
}

// ===========================
// 游客本地历史类型
// ===========================
export interface LocalGuestHistoryItem {
  pasteId: string
  adminKey: string
  encryptionKey: string
  title?: string | null
  status?: 'published' | 'edited'
  isDeleted: false
  isGuest: true
  localCreatedAt: number
}

// ===========================
// 游客历史本地操作
// ===========================
export function loadGuestHistory(): LocalGuestHistoryItem[] {
  try {
    const raw = localStorage.getItem(GUEST_HISTORY_KEY)
    if (!raw) return []
    return JSON.parse(raw) as LocalGuestHistoryItem[]
  } catch {
    return []
  }
}

function saveGuestHistory(items: LocalGuestHistoryItem[]): void {
  localStorage.setItem(GUEST_HISTORY_KEY, JSON.stringify(items))
}

export function addGuestHistoryItem(
  pasteId: string,
  adminKey: string,
  encryptionKey: string,
  opts?: {
    title?: string | null
    status?: 'published' | 'edited'
  }
): void {
  const items = loadGuestHistory()
  const idx = items.findIndex((i) => i.pasteId === pasteId)
  const normalizedTitle = typeof opts?.title === 'string' ? opts.title.trim() : ''
  const item: LocalGuestHistoryItem = {
    pasteId,
    adminKey,
    encryptionKey,
    title: normalizedTitle || null,
    status: opts?.status ?? 'published',
    isDeleted: false,
    isGuest: true,
    localCreatedAt: Date.now()
  }
  if (idx >= 0) {
    items[idx] = item
  } else {
    items.unshift(item)
  }
  saveGuestHistory(items)
}

export function removeGuestHistoryItem(pasteId: string): void {
  const items = loadGuestHistory().filter((i) => i.pasteId !== pasteId)
  saveGuestHistory(items)
}

function removeGuestHistoryItems(pasteIds: string[]): void {
  if (pasteIds.length === 0) return
  const set = new Set(pasteIds)
  const items = loadGuestHistory().filter((i) => !set.has(i.pasteId))
  saveGuestHistory(items)
}

export function clearGuestHistory(): void {
  localStorage.removeItem(GUEST_HISTORY_KEY)
}

function toGuestHistoryListItem(item: LocalGuestHistoryItem): HistoryListItem {
  const createdAt =
    typeof item.localCreatedAt === 'number' && Number.isFinite(item.localCreatedAt)
      ? item.localCreatedAt
      : Date.now()
  const iso = new Date(createdAt).toISOString()
  const status = item.status === 'edited' ? 'edited' : 'published'
  const title = typeof item.title === 'string' ? item.title.trim() : ''

  return {
    paste_id: item.pasteId,
    status,
    title: title || null,
    max_views: -1,
    view_count: 0,
    is_starred: false,
    published_at: null,
    paste_updated_at: iso,
    history_updated_at: iso,
    expire_at: null
  }
}

function guestCreatedAt(item: LocalGuestHistoryItem): number {
  return typeof item.localCreatedAt === 'number' && Number.isFinite(item.localCreatedAt)
    ? item.localCreatedAt
    : 0
}

// ===========================
// 用户历史本地缓存操作
// ===========================
function loadUserHistoryCache(userId: number): HistoryListItem[] {
  try {
    const raw = localStorage.getItem(userHistoryKey(userId))
    if (!raw) return []
    return JSON.parse(raw) as HistoryListItem[]
  } catch {
    return []
  }
}

function saveUserHistoryCache(userId: number, items: HistoryListItem[]): void {
  localStorage.setItem(userHistoryKey(userId), JSON.stringify(items))
}

export function clearUserHistoryCache(userId: number): void {
  localStorage.removeItem(userHistoryKey(userId))
}

// ===========================
// useHistory composable（单例）
// ===========================
const historyItems = ref<HistoryListItem[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyLimit = ref(20)
const historyLoading = ref(false)
const historySearch = ref('')
const historyStarredFilter = ref<boolean | null>(null)

export function resetHistoryState(): void {
  historyItems.value = []
  historyTotal.value = 0
  historyPage.value = 1
  historyLoading.value = false
  historySearch.value = ''
  historyStarredFilter.value = null
}

export function useHistory() {
  const hasMore = computed(
    () => historyPage.value * historyLimit.value < historyTotal.value
  )

  async function fetchHistory(opts: {
    page?: number
    reset?: boolean
    search?: string
    starred?: boolean | null
  } = {}, userId?: number | null) {
    const requestedPage = opts.page ?? (opts.reset ? 1 : historyPage.value)
    if (opts.reset) {
      historyItems.value = []
      historyPage.value = 1
    }
    if (opts.search !== undefined) historySearch.value = opts.search
    if (opts.starred !== undefined) historyStarredFilter.value = opts.starred

    historyLoading.value = true
    try {
      if (userId == null) {
        const keyword = historySearch.value.trim().toLowerCase()
        const guestItems = loadGuestHistory()
          .filter((i) => !i.isDeleted)
          .filter((i) => {
            if (!keyword) return true
            const title = typeof i.title === 'string' ? i.title.trim().toLowerCase() : ''
            return title.includes(keyword)
          })
          .sort((a, b) => guestCreatedAt(b) - guestCreatedAt(a))
          .map(toGuestHistoryListItem)

        const visibleItems = historyStarredFilter.value === true ? [] : guestItems
        const total = visibleItems.length
        const totalPages = Math.max(1, Math.ceil(total / historyLimit.value))
        const safePage = Math.min(Math.max(requestedPage, 1), totalPages)
        const start = (safePage - 1) * historyLimit.value
        historyItems.value = visibleItems.slice(start, start + historyLimit.value)
        historyTotal.value = total
        historyPage.value = safePage
        return
      }

      const params: Record<string, unknown> = {
        page: requestedPage,
        limit: historyLimit.value
      }
      if (historySearch.value) params.search = historySearch.value
      if (historyStarredFilter.value !== null) params.starred = historyStarredFilter.value

      let resp = await getHistory(params)
      const totalPages = Math.max(1, Math.ceil(resp.total / historyLimit.value))
      const safePage = Math.min(Math.max(requestedPage, 1), totalPages)

      if (safePage !== requestedPage && resp.total > 0) {
        resp = await getHistory({
          ...params,
          page: safePage
        })
      }

      historyItems.value = resp.items
      historyTotal.value = resp.total
      historyPage.value = safePage
      if (!historySearch.value && historyStarredFilter.value === null && historyPage.value === 1) {
        saveUserHistoryCache(userId, historyItems.value)
      }
    } finally {
      historyLoading.value = false
    }
  }

  async function loadMore(userId?: number | null) {
    if (userId == null) return
    if (!hasMore.value || historyLoading.value) return
    await fetchHistory({ page: historyPage.value + 1 }, userId)
  }

  async function addToHistory(
    pasteId: string,
    adminKey: string,
    encryptionKey: string,
    userId: number | null,
    guestMeta?: {
      title?: string | null
      status?: 'published' | 'edited'
    }
  ): Promise<void> {
    if (userId == null) {
      // 游客：写本地
      addGuestHistoryItem(pasteId, adminKey, encryptionKey, guestMeta)
      return
    }
    // 已登录：调服务端
    try {
      const detail = await saveToHistory(pasteId, adminKey, encryptionKey)
      // 更新本地列表（插入到头部，或更新已有项）
      const idx = historyItems.value.findIndex((i) => i.paste_id === pasteId)
      const listItem: HistoryListItem = {
        paste_id: detail.paste_id,
        status: detail.status,
        title: detail.title,
        max_views: detail.max_views,
        view_count: detail.view_count,
        is_starred: detail.is_starred,
        published_at: detail.published_at,
        paste_updated_at: detail.paste_updated_at,
        history_updated_at: detail.history_updated_at,
        expire_at: detail.expire_at
      }
      if (idx >= 0) {
        historyItems.value[idx] = listItem
      } else {
        historyItems.value.unshift(listItem)
        historyTotal.value++
      }
      // 同步本地缓存
      saveUserHistoryCache(userId, historyItems.value)
    } catch (e) {
      console.error('保存历史失败:', e)
    }
  }

  async function toggleStar(pasteId: string, isStarred: boolean, userId: number): Promise<void> {
    await starHistory(pasteId, isStarred)
    const idx = historyItems.value.findIndex((i) => i.paste_id === pasteId)
    if (idx >= 0) {
      historyItems.value[idx] = { ...historyItems.value[idx], is_starred: isStarred } as HistoryListItem
      saveUserHistoryCache(userId, historyItems.value)
    }
  }

  async function removeFromHistory(pasteId: string, userId: number | null): Promise<void> {
    if (userId == null) {
      removeGuestHistoryItem(pasteId)
      historyItems.value = historyItems.value.filter((i) => i.paste_id !== pasteId)
      historyTotal.value = Math.max(0, historyTotal.value - 1)
      return
    }
    await deleteHistory(pasteId)
    historyItems.value = historyItems.value.filter((i) => i.paste_id !== pasteId)
    historyTotal.value = Math.max(0, historyTotal.value - 1)
    saveUserHistoryCache(userId, historyItems.value)
  }

  async function importGuestAndSync(userId: number): Promise<void> {
    const guestItems = loadGuestHistory().filter((i) => !i.isDeleted)
    if (guestItems.length === 0) {
      clearGuestHistory()
      return
    }

    const importItems: ImportGuestItem[] = guestItems.map((i) => ({
      paste_id: i.pasteId,
      admin_key: i.adminKey,
      encryption_key: i.encryptionKey
    }))

    try {
      const resp = await importGuestHistory(importItems)
      // 用服务端快照覆盖本地
      historyItems.value = resp.snapshot.items
      historyTotal.value = resp.snapshot.total
      historyPage.value = 1
      saveUserHistoryCache(userId, resp.snapshot.items)
      removeGuestHistoryItems(resp.imported_ids)
      if (resp.skipped === 0) {
        clearGuestHistory()
      }
    } catch (e) {
      console.error('导入游客历史失败:', e)
    }
  }

  function initFromCache(userId: number): void {
    const cached = loadUserHistoryCache(userId)
    if (cached.length > 0) {
      historyItems.value = cached
      historyTotal.value = cached.length
      historyPage.value = 1
    } else {
      historyItems.value = []
      historyTotal.value = 0
      historyPage.value = 1
    }
  }

  return {
    historyItems,
    historyTotal,
    historyPage,
    historyLimit,
    historyLoading,
    historySearch,
    historyStarredFilter,
    hasMore,
    fetchHistory,
    loadMore,
    addToHistory,
    toggleStar,
    removeFromHistory,
    importGuestAndSync,
    initFromCache
  }
}
