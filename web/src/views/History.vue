<template>
  <div class="history-page">
    <div class="page-header">
      <h1 class="page-title">历史记录</h1>
    </div>

    <!-- 搜索和筛选栏 -->
    <div class="filter-bar">
      <mdui-text-field
        v-model="searchInput"
        label="搜索标题"
        clearable
        variant="outlined"
        class="search-field"
        @keydown.enter="handleSearch"
        @clear="handleClearSearch"
      >
        <mdui-icon slot="icon" name="search"></mdui-icon>
      </mdui-text-field>

      <mdui-segmented-button-group
        :value="starredFilter"
        @change="handleStarredFilterChange"
        selects="single"
      >
        <mdui-segmented-button value="all">全部</mdui-segmented-button>
        <mdui-segmented-button value="starred">已收藏</mdui-segmented-button>
      </mdui-segmented-button-group>

      <mdui-button-icon @click="handleRefresh" :disabled="historyLoading">
        <mdui-icon name="refresh"></mdui-icon>
      </mdui-button-icon>
    </div>

    <!-- 加载中 -->
    <div v-if="historyLoading && historyItems.length === 0" class="loading-state">
      <mdui-circular-progress></mdui-circular-progress>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!historyLoading && historyItems.length === 0" class="empty-state">
      <mdui-icon name="history" class="empty-icon"></mdui-icon>
      <p>暂无历史记录</p>
    </div>

    <!-- 历史记录列表（折叠面板） -->
    <div v-else class="history-list-wrapper">
      <mdui-collapse class="history-collapse">
        <mdui-collapse-item
          v-for="item in historyItems"
          :key="item.paste_id"
          :value="item.paste_id"
          class="history-collapse-item"
        >
          <div slot="header" class="history-item-header">
            <div class="title-cell">
              <mdui-icon
                v-if="item.is_starred"
                name="star"
                class="star-icon starred"
              ></mdui-icon>
              <mdui-icon
                v-else
                name="star_border"
                class="star-icon"
              ></mdui-icon>
              <span class="title-text">{{ item.title || '(无标题)' }}</span>
            </div>
            <div class="meta-cell">
              <span class="status-badge" :data-status="item.status">
                {{ statusLabel(item.status) }}
              </span>
              <span v-if="showViewsColumn" class="views-text">
                <template v-if="item.max_views === -1">{{ item.view_count }}</template>
                <template v-else>{{ item.view_count }} / {{ item.max_views }}</template>
              </span>
              <span class="time-text">{{ formatTime(item.history_updated_at) }}</span>
            </div>
          </div>

          <div class="history-item-actions">
            <mdui-button-icon
              class="circle-action"
              :title="item.is_starred ? '取消收藏' : '收藏'"
              @click="handleToggleStar(item)"
            >
              <mdui-icon :name="item.is_starred ? 'star' : 'star_border'"></mdui-icon>
            </mdui-button-icon>
            <mdui-button-icon class="circle-action" title="查看" @click="handleView(item)">
              <mdui-icon name="open_in_new"></mdui-icon>
            </mdui-button-icon>
            <mdui-button-icon class="circle-action" title="编辑" @click="handleEdit(item)">
              <mdui-icon name="edit"></mdui-icon>
            </mdui-button-icon>
            <mdui-button-icon class="circle-action" title="删除" @click="handleDelete(item)">
              <mdui-icon name="delete_outline"></mdui-icon>
            </mdui-button-icon>
          </div>
        </mdui-collapse-item>
      </mdui-collapse>

      <div class="pagination-wrapper" v-if="historyTotal > 0">
        <div class="pagination-summary">共 {{ historyTotal }} 条 · 第 {{ historyPage }} / {{ totalPages }} 页</div>
        <div class="pagination-controls">
          <mdui-button-icon
            class="circle-action"
            title="上一页"
            :disabled="historyLoading || historyPage <= 1"
            @click="goToPage(historyPage - 1)"
          >
            <mdui-icon name="chevron_left"></mdui-icon>
          </mdui-button-icon>
          <mdui-button-icon
            class="circle-action"
            title="下一页"
            :disabled="historyLoading || historyPage >= totalPages"
            @click="goToPage(historyPage + 1)"
          >
            <mdui-icon name="chevron_right"></mdui-icon>
          </mdui-button-icon>

          <mdui-text-field
            v-model="jumpPageInput"
            class="jump-field"
            label="跳转页码"
            type="number"
            variant="outlined"
            min="1"
            step="1"
            inputmode="numeric"
            :max="totalPages"
            @keydown.enter.prevent="handleJumpPage"
          ></mdui-text-field>
          <mdui-button variant="tonal" :disabled="!canJumpPage" @click="handleJumpPage">
            跳转
          </mdui-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/icon.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/segmented-button-group.js'
import 'mdui/components/segmented-button.js'
import 'mdui/components/collapse.js'
import 'mdui/components/collapse-item.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import { dialog } from 'mdui/functions/dialog.js'
import type { HistoryListItem } from '../services/history'
import { getHistoryDetail } from '../services/history'
import { useHistory, loadGuestHistory } from '../composables/useHistory'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const route = useRoute()
const { currentUser } = useAuth()
const {
  historyItems,
  historyTotal,
  historyPage,
  historyLimit,
  historyLoading,
  historySearch,
  fetchHistory,
  toggleStar,
  removeFromHistory,
  initFromCache
} = useHistory()

type StarredFilterValue = 'all' | 'starred'

interface HistoryRouteState {
  page: number
  search: string
  starred: StarredFilterValue
}

interface FetchHistoryOptions {
  page?: number
  reset?: boolean
  search?: string
  starred?: boolean | null
}

const searchInput = ref('')
const starredFilter = ref<StarredFilterValue>('all')
const jumpPageInput = ref('1')
const showViewsColumn = computed(() => !!currentUser.value)
const totalPages = computed(() => Math.max(1, Math.ceil(historyTotal.value / historyLimit.value)))
const canJumpPage = computed(() => {
  if (historyLoading.value) return false
  const page = parsePositiveInteger(jumpPageInput.value)
  if (page === null) return false
  if (page < 1 || page > totalPages.value) return false
  return page !== historyPage.value
})
const USER_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone
const HAS_TZ_SUFFIX_RE = /(Z|[+\-]\d{2}:\d{2})$/i
const EDIT_CONTEXT_STORAGE_KEY = 'mb_editor_edit_context_v1'

watch(
  historyPage,
  (page) => {
    jumpPageInput.value = String(page)
  },
  { immediate: true }
)

function currentUserId(): number | null {
  return currentUser.value?.id ?? null
}

function firstQueryValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return ''
}

function parsePositiveInteger(value: string): number | null {
  const normalized = value.trim()
  if (!/^\d+$/.test(normalized)) return null

  const parsed = Number(normalized)
  if (!Number.isSafeInteger(parsed) || parsed < 1) return null
  return parsed
}

function parseRouteState(): HistoryRouteState {
  const search = firstQueryValue(route.query.search).trim()
  const starred = firstQueryValue(route.query.starred).trim() === 'starred' ? 'starred' : 'all'
  const parsedPage = parsePositiveInteger(firstQueryValue(route.query.page))

  return {
    page: parsedPage ?? 1,
    search,
    starred
  }
}

function syncRouteQueryFromState() {
  const desiredPage = historyPage.value > 1 ? String(historyPage.value) : ''
  const desiredSearch = historySearch.value.trim()
  const desiredStarred = starredFilter.value === 'starred' ? 'starred' : ''
  const currentPage = firstQueryValue(route.query.page).trim()
  const currentSearch = firstQueryValue(route.query.search).trim()
  const currentStarred = firstQueryValue(route.query.starred).trim()

  if (
    currentPage === desiredPage &&
    currentSearch === desiredSearch &&
    currentStarred === desiredStarred
  ) {
    return
  }

  const nextQuery: LocationQueryRaw = { ...route.query }
  if (desiredPage) {
    nextQuery.page = desiredPage
  } else {
    delete nextQuery.page
  }
  if (desiredSearch) {
    nextQuery.search = desiredSearch
  } else {
    delete nextQuery.search
  }
  if (desiredStarred) {
    nextQuery.starred = desiredStarred
  } else {
    delete nextQuery.starred
  }

  void router.replace({ query: nextQuery })
}

async function fetchHistoryAndSyncRoute(opts: FetchHistoryOptions = {}) {
  const applied = await fetchHistory(opts, currentUserId())
  if (!applied) return
  syncRouteQueryFromState()
}

async function applyRouteQuery() {
  const state = parseRouteState()
  const searchChanged = historySearch.value !== state.search
  const filterChanged = starredFilter.value !== state.starred
  const pageChanged = historyPage.value !== state.page

  if (!searchChanged && !filterChanged && !pageChanged) {
    if (searchInput.value !== state.search) {
      searchInput.value = state.search
    }
    syncRouteQueryFromState()
    return
  }

  searchInput.value = state.search
  starredFilter.value = state.starred
  await fetchHistoryAndSyncRoute({
    page: state.page,
    reset: searchChanged || filterChanged,
    search: state.search,
    starred: state.starred === 'starred' ? true : null
  })
}

function statusLabel(status: string): string {
  if (status === 'published') return '已发布'
  if (status === 'edited') return '已编辑'
  return status
}

function parseUtcToLocalDate(raw: string): Date {
  const value = raw.trim()
  if (!value) return new Date(Number.NaN)

  const normalized = HAS_TZ_SUFFIX_RE.test(value) ? value : `${value}Z`
  const parsed = new Date(normalized)
  if (!Number.isNaN(parsed.getTime())) {
    return parsed
  }

  return new Date(value)
}

function formatTime(iso: string): string {
  const d = parseUtcToLocalDate(iso)
  if (Number.isNaN(d.getTime())) return '-'

  const now = new Date()
  const diff = Math.max(0, now.getTime() - d.getTime())
  const days = Math.floor(diff / 86400000)
  if (days === 0) {
    return d.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: USER_TIMEZONE
    })
  }
  if (days < 7) return `${days}天前`
  return d.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    timeZone: USER_TIMEZONE
  })
}

function handleSearch() {
  void fetchHistoryAndSyncRoute({ reset: true, search: searchInput.value })
}

function eventValue(e: Event): string {
  const target = e.target as HTMLInputElement | { value?: unknown } | null
  const value = target && 'value' in target ? target.value : ''
  return typeof value === 'string' ? value : value == null ? '' : String(value)
}

function handleClearSearch() {
  searchInput.value = ''
  void fetchHistoryAndSyncRoute({ reset: true, search: '' })
}

function handleStarredFilterChange(e: Event) {
  const val = eventValue(e)
  if (!val) return
  starredFilter.value = val === 'starred' ? 'starred' : 'all'
  const starred = val === 'starred' ? true : null
  void fetchHistoryAndSyncRoute({ reset: true, starred })
}

function handleRefresh() {
  void fetchHistoryAndSyncRoute({ page: historyPage.value, search: searchInput.value })
}

function goToPage(page: number) {
  const target = Math.min(Math.max(Math.trunc(page), 1), totalPages.value)
  if (target === historyPage.value) return
  void fetchHistoryAndSyncRoute({ page: target })
}

function handleJumpPage() {
  const raw = jumpPageInput.value.trim()
  if (!raw) {
    snackbar({ message: '请输入页码', closeable: true })
    jumpPageInput.value = String(historyPage.value)
    return
  }

  const page = parsePositiveInteger(raw)
  if (page === null) {
    snackbar({ message: '请输入正整数页码', closeable: true })
    jumpPageInput.value = String(historyPage.value)
    return
  }
  if (page > totalPages.value) {
    snackbar({ message: `页码范围：1 - ${totalPages.value}`, closeable: true })
    jumpPageInput.value = String(historyPage.value)
    return
  }

  goToPage(page)
}

function navigateToEditor(pasteId: string, adminKey: string, encryptionKey: string) {
  try {
    sessionStorage.setItem(
      EDIT_CONTEXT_STORAGE_KEY,
      JSON.stringify({
        paste_id: pasteId,
        admin_key: adminKey,
        encryption_key: encryptionKey,
        created_at: Date.now()
      })
    )
  } catch {
    snackbar({ message: '浏览器存储不可用，无法进入编辑模式', closeable: true })
    return
  }

  void router.push({
    path: '/',
    query: {
      edit: '1',
      paste_id: pasteId
    }
  })
}

async function handleView(item: HistoryListItem) {
  if (!currentUser.value) {
    const guestItem = loadGuestHistory().find((i) => i.pasteId === item.paste_id)
    const url = `/p/${item.paste_id}${guestItem?.encryptionKey ? '#' + guestItem.encryptionKey : ''}`
    window.open(url, '_blank')
    return
  }

  try {
    const detail = await getHistoryDetail(item.paste_id)
    const url = `/p/${item.paste_id}${detail.encryption_key ? '#' + detail.encryption_key : ''}`
    window.open(url, '_blank')
  } catch {
    // 如果获取详情失败，直接跳转（可能是公开paste）
    router.push(`/p/${item.paste_id}`)
  }
}

async function handleEdit(item: HistoryListItem) {
  if (!currentUser.value) {
    const guestItem = loadGuestHistory().find((i) => i.pasteId === item.paste_id)
    if (!guestItem?.adminKey || !guestItem.encryptionKey) {
      snackbar({ message: '缺少编辑所需密钥', closeable: true })
      return
    }
    navigateToEditor(item.paste_id, guestItem.adminKey, guestItem.encryptionKey)
    return
  }

  try {
    const detail = await getHistoryDetail(item.paste_id)
    navigateToEditor(item.paste_id, detail.admin_key, detail.encryption_key)
  } catch {
    snackbar({ message: '获取编辑信息失败', closeable: true })
  }
}

async function handleToggleStar(item: HistoryListItem) {
  if (!currentUser.value) return
  try {
    const nextStarred = !item.is_starred
    await toggleStar(item.paste_id, nextStarred, currentUser.value.id)
    if (starredFilter.value === 'starred' && !nextStarred) {
      const targetPage = Math.min(historyPage.value, totalPages.value)
      await fetchHistoryAndSyncRoute({ page: targetPage })
    }
  } catch {
    snackbar({ message: '操作失败', closeable: true })
  }
}

function handleDelete(item: HistoryListItem) {
  dialog({
    headline: '删除历史记录',
    description: `确定要从历史记录中移除「${item.title || item.paste_id}」吗？`,
    actions: [
      { text: '取消' },
      {
        text: '删除',
        onClick: async () => {
          try {
            await removeFromHistory(item.paste_id, currentUser.value?.id ?? null)
            const targetPage = Math.min(historyPage.value, totalPages.value)
            await fetchHistoryAndSyncRoute({ page: targetPage })
            snackbar({ message: '已删除' })
          } catch {
            snackbar({ message: '删除失败', closeable: true })
          }
        }
      }
    ]
  })
}

onMounted(() => {
  const userId = currentUserId()
  if (userId !== null) {
    initFromCache(userId)
  }
  const state = parseRouteState()
  searchInput.value = state.search
  starredFilter.value = state.starred

  void fetchHistoryAndSyncRoute({
    page: state.page,
    reset: true,
    search: state.search,
    starred: state.starred === 'starred' ? true : null
  })
})

watch(
  [() => route.query.page, () => route.query.search, () => route.query.starred],
  () => {
    void applyRouteQuery()
  }
)
</script>

<style scoped>
.history-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface));
  margin: 0;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-field {
  flex: 1;
  min-width: 200px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
  gap: 16px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.empty-icon {
  font-size: 48px;
  opacity: 0.4;
}

.history-list-wrapper {
  display: grid;
  gap: 16px;
}

.history-collapse {
  display: grid;
  gap: 10px;
}

.history-collapse-item {
  border: 1px solid rgb(var(--mdui-color-outline-variant));
  border-radius: 12px;
  background: rgb(var(--mdui-color-surface-container-low));
}

.history-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
}

.meta-cell {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.views-text,
.time-text {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
  white-space: nowrap;
}

.history-item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px 14px;
  flex-wrap: wrap;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.star-icon {
  font-size: 18px;
  color: rgb(var(--mdui-color-on-surface-variant));
  flex-shrink: 0;
}

.star-icon.starred {
  color: rgb(var(--mdui-color-primary));
}

.title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  background: rgb(var(--mdui-color-surface-container-high));
  color: rgb(var(--mdui-color-on-surface-variant));
}

.status-badge[data-status='published'] {
  background: rgb(var(--mdui-color-primary-container));
  color: rgb(var(--mdui-color-on-primary-container));
}

.circle-action {
  border-radius: 999px;
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 8px 0 2px;
}

.pagination-summary {
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.jump-field {
  width: 130px;
}

@media (max-width: 768px) {
  .history-item-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .meta-cell {
    width: 100%;
    justify-content: flex-start;
  }

  .title-text {
    max-width: 100%;
  }
}
</style>
