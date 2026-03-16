<template>
  <div class="history-page">
    <div class="page-header">
      <h1 class="page-title">历史记录</h1>
    </div>

    <section class="history-surface history-filters" aria-label="历史记录筛选和操作">
      <div class="history-surface-header">
        <div>
          <div class="history-surface-eyebrow">筛选</div>
          <div class="history-surface-title">搜索与视图选项</div>
        </div>
      </div>

      <div class="filter-bar">
        <mdui-text-field
          v-model="searchInput"
          label="搜索标题"
          clearable
          variant="outlined"
          class="search-field"
          @keydown.enter="handleSearch"
          @clear="handleClearSearch"
        ></mdui-text-field>

        <mdui-segmented-button-group
          class="history-filter-group"
          :value="starredFilter"
          @change="handleStarredFilterChange"
          selects="single"
        >
          <mdui-segmented-button value="all">全部</mdui-segmented-button>
          <mdui-segmented-button value="starred">已收藏</mdui-segmented-button>
        </mdui-segmented-button-group>

        <mdui-button
          class="filter-search-button"
          variant="filled"
          :disabled="historyLoading"
          @click="handleSearch"
        >
          搜索
        </mdui-button>
      </div>
    </section>

    <section class="history-surface history-results" :aria-busy="historyLoading ? 'true' : 'false'">
      <div class="history-surface-header history-results-header">
        <div>
          <div class="history-surface-eyebrow">结果</div>
          <div class="history-surface-title">{{ resultsHeadline }}</div>
        </div>
      </div>

      <div v-if="historyLoading && historyItems.length === 0" class="loading-state" role="status">
        <mdui-circular-progress></mdui-circular-progress>
        <div class="state-copy">正在加载历史记录…</div>
      </div>

      <div v-else-if="!historyLoading && historyItems.length === 0" class="empty-state" role="status">
        <div class="empty-icon-wrap" aria-hidden="true">
          <mdui-icon :name="emptyState.icon" class="empty-icon"></mdui-icon>
        </div>
        <div class="empty-title">{{ emptyState.title }}</div>
        <p class="empty-copy">{{ emptyState.copy }}</p>
      </div>

      <div v-else class="history-list-wrapper">
        <mdui-collapse class="history-collapse">
          <mdui-collapse-item
            v-for="item in historyItems"
            :key="item.paste_id"
            :value="item.paste_id"
            class="history-collapse-item"
          >
            <div slot="header" class="history-item-header">
              <div class="history-item-main">
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
                    浏览 {{ item.max_views === -1 ? item.view_count : `${item.view_count} / ${item.max_views}` }}
                  </span>
                  <span class="time-text">{{ formatTime(item.history_updated_at) }}</span>
                </div>
              </div>
            </div>

            <div class="history-item-actions" role="group" :aria-label="`历史记录 ${item.title || item.paste_id} 的操作`">
              <mdui-button-icon
                class="circle-action"
                :title="item.is_starred ? '取消收藏' : '收藏'"
                :aria-label="item.is_starred ? '取消收藏' : '收藏此记录'"
                :aria-pressed="item.is_starred ? 'true' : 'false'"
                @click="handleToggleStar(item)"
              >
                <mdui-icon :name="item.is_starred ? 'star' : 'star_border'"></mdui-icon>
              </mdui-button-icon>
              <mdui-button-icon class="circle-action" title="查看" aria-label="查看记录" @click="handleView(item)">
                <mdui-icon name="open_in_new"></mdui-icon>
              </mdui-button-icon>
              <mdui-button-icon class="circle-action" title="编辑" aria-label="编辑记录" @click="handleEdit(item)">
                <mdui-icon name="edit"></mdui-icon>
              </mdui-button-icon>
              <mdui-button-icon class="circle-action" title="删除" aria-label="删除记录" @click="handleDelete(item)">
                <mdui-icon name="delete_outline"></mdui-icon>
              </mdui-button-icon>
            </div>
          </mdui-collapse-item>
        </mdui-collapse>

        <PaginationFooter
          v-if="historyTotal > 0"
          :total="historyTotal"
          :page="historyPage"
          :total-pages="totalPages"
          :loading="historyLoading"
          show-jump
          @change-page="goToPage"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import 'mdui/components/button.js'
import 'mdui/components/text-field.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/icon.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/segmented-button-group.js'
import 'mdui/components/segmented-button.js'
import 'mdui/components/collapse.js'
import 'mdui/components/collapse-item.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import { dialog } from 'mdui/functions/dialog.js'
import PaginationFooter from '../components/common/PaginationFooter.vue'
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
const showViewsColumn = computed(() => !!currentUser.value)
const totalPages = computed(() => Math.max(1, Math.ceil(historyTotal.value / historyLimit.value)))
const hasActiveFilters = computed(() => historySearch.value.trim().length > 0 || starredFilter.value === 'starred')
const resultsHeadline = computed(() => (starredFilter.value === 'starred' ? '已收藏记录' : '全部历史记录'))
const emptyState = computed(() => {
  if (hasActiveFilters.value) {
    return {
      icon: 'search_off',
      title: '没有匹配的历史记录',
      copy: '尝试清空搜索条件或切换回全部记录，以查看更多内容。'
    }
  }

  if (currentUser.value) {
    return {
      icon: 'history',
      title: '你的历史记录还是空的',
      copy: '当你保存、编辑或收藏内容后，这里会自动显示对应的记录。'
    }
  }

  return {
    icon: 'history_toggle_off',
    title: '还没有本地历史记录',
    copy: '访客模式下的浏览器历史会显示在这里；登录后可查看账户级历史。'
  }
})
const USER_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone
const HAS_TZ_SUFFIX_RE = /(Z|[+\-]\d{2}:\d{2})$/i
const EDIT_CONTEXT_STORAGE_KEY = 'mb_editor_edit_context_v1'

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
  void fetchHistoryAndSyncRoute({ reset: true, starred, search: searchInput.value })
}

function goToPage(page: number) {
  const target = Math.min(Math.max(Math.trunc(page), 1), totalPages.value)
  if (target === historyPage.value) return
  void fetchHistoryAndSyncRoute({ page: target })
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
  display: grid;
  gap: 20px;
}

.page-header {
  display: grid;
}

.page-title {
  font-size: clamp(1.7rem, 2vw, 2.1rem);
  font-weight: 700;
  color: rgb(var(--mdui-color-on-surface));
  margin: 0;
}

.history-surface {
  display: grid;
  gap: 18px;
  padding: 20px;
  border-radius: 24px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.72);
  background: rgb(var(--mdui-color-surface));
}

.history-filters {
  background: rgb(var(--mdui-color-surface-container-low));
}

.history-results {
  min-height: 240px;
  gap: 0;
  padding: 0;
}

.history-surface-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.history-results-header {
  padding: 20px 20px 18px;
}

.history-surface-eyebrow {
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.history-surface-title {
  margin-top: 4px;
  font-size: 1.08rem;
  font-weight: 600;
  line-height: 1.35;
  color: rgb(var(--mdui-color-on-surface));
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.search-field {
  flex: 1 1 320px;
  min-width: 0;
}

.history-filter-group {
  flex: 0 1 auto;
  max-width: 100%;
}

.filter-search-button {
  flex: 0 0 auto;
  margin-inline-start: auto;
  min-width: 108px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 16px;
  color: rgb(var(--mdui-color-on-surface-variant));
  text-align: center;
}

.state-copy,
.empty-copy {
  margin: 0;
  max-width: 34rem;
  font-size: 0.94rem;
  line-height: 1.6;
}

.empty-title {
  font-size: 1.08rem;
  font-weight: 600;
  line-height: 1.35;
  color: rgb(var(--mdui-color-on-surface));
}

.empty-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: rgb(var(--mdui-color-surface-container-low));
}

.empty-icon {
  font-size: 32px;
  opacity: 0.72;
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
  overflow: hidden;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.72);
  border-radius: 20px;
  background: rgb(var(--mdui-color-surface-container-low));
}

.history-item-header {
  padding: 16px 20px 8px;
}

.history-item-main {
  display: grid;
  gap: 10px;
}

.meta-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  min-width: 0;
}

.views-text,
.time-text {
  font-size: 0.79rem;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.history-item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px 18px;
  flex-wrap: wrap;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
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
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.35;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 0.78rem;
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

@media (max-width: 768px) {
  .history-surface {
    padding: 18px;
  }

  .history-results {
    padding: 0;
  }

  .history-results-header {
    padding: 18px 18px 16px;
  }

  .history-surface-header,
  .history-results-header {
    flex-direction: column;
  }

  .search-field,
  .history-filter-group,
  .filter-search-button {
    flex-basis: 100%;
  }

  .filter-search-button {
    margin-inline-start: 0;
  }

  .title-text {
    white-space: normal;
  }
}

@media (max-width: 640px) {
  .history-page {
    padding: 20px 12px;
  }

  .history-surface {
    padding: 16px;
    border-radius: 20px;
  }

  .history-results {
    padding: 0;
  }

  .history-results-header {
    padding: 16px 16px 14px;
  }

  .history-item-header {
    padding: 14px 16px 8px;
  }

  .history-item-actions {
    padding: 0 16px 16px;
  }
}
</style>
