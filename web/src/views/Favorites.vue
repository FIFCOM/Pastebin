<template>
  <div class="favorites-page" data-stagger>
    <div class="page-header">
      <h1 class="page-title">收藏</h1>
    </div>

    <section class="favorites-surface favorites-filters" aria-label="收藏搜索和操作">
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

        <mdui-button
          class="filter-search-button"
          variant="filled"
          :disabled="favoriteLoading"
          @click="handleSearch"
        >
          搜索
        </mdui-button>
      </div>
    </section>

    <section class="favorites-surface favorites-results" :aria-busy="favoriteLoading ? 'true' : 'false'">
      <div class="favorites-surface-header favorites-results-header">
        <div>
          <div class="result-header-title">{{ resultsHeadline }}</div>
        </div>
      </div>

      <div v-if="isInitialFavoritesLoading" class="loading-state" role="status">
        <mdui-circular-progress></mdui-circular-progress>
        <div class="state-copy">正在加载收藏…</div>
      </div>

      <div v-else-if="!favoriteLoading && favoriteItems.length === 0" class="empty-state" role="status">
        <div class="empty-icon-wrap" aria-hidden="true">
          <mdui-icon :name="emptyState.icon" class="empty-icon"></mdui-icon>
        </div>
        <div class="empty-title">{{ emptyState.title }}</div>
        <p class="empty-copy">{{ emptyState.copy }}</p>
      </div>

      <div v-else class="favorites-list-wrapper">
        <mdui-collapse
          ref="favoritesCollapseRef"
          class="favorites-collapse"
          @change="syncExpandedFavoriteItems"
        >
          <mdui-collapse-item
            v-for="item in favoriteItems"
            :key="item.paste_id"
            :value="item.paste_id"
            class="favorites-collapse-item"
          >
            <div slot="header" class="favorites-item-header">
              <div class="favorites-item-main">
                <div class="title-cell">
                  <span class="title-text">{{ item.title || '(无标题)' }}</span>
                </div>

                <div class="meta-cell">
                  <span class="status-badge" :data-status="item.status">
                    {{ statusLabel(item.status) }}
                  </span>
                  <span class="views-text">
                    浏览 {{ item.max_views === -1 ? item.view_count : `${item.view_count} / ${item.max_views}` }}
                  </span>
                  <span class="time-text">收藏于 {{ formatTime(item.favorite_updated_at) }}</span>
                </div>
              </div>
            </div>

            <div
              class="favorites-item-actions"
              role="group"
              :aria-hidden="isFavoriteItemExpanded(item.paste_id) ? undefined : 'true'"
              :inert="isFavoriteItemExpanded(item.paste_id) ? undefined : true"
              :aria-label="`收藏 ${item.title || item.paste_id} 的操作`"
            >
              <mdui-button class="favorites-action-button" variant="tonal" @click.stop="handleView(item)">
                <mdui-icon slot="icon" name="open_in_new"></mdui-icon>
                打开
              </mdui-button>
              <mdui-button
                class="favorites-action-button favorites-action-button--remove"
                variant="outlined"
                @click.stop="handleRemove(item)"
              >
                <mdui-icon slot="icon" name="star"></mdui-icon>
                取消收藏
              </mdui-button>
            </div>
          </mdui-collapse-item>
        </mdui-collapse>

        <PaginationFooter
          v-if="favoriteTotal > 0"
          :total="favoriteTotal"
          :page="favoritePage"
          :total-pages="totalPages"
          :loading="favoriteLoading"
          show-jump
          @change-page="goToPage"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import 'mdui/components/button.js'
import 'mdui/components/text-field.js'
import 'mdui/components/icon.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/collapse.js'
import 'mdui/components/collapse-item.js'
import type { Collapse } from 'mdui/components/collapse.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import { dialog } from 'mdui/functions/dialog.js'
import PaginationFooter from '../components/common/PaginationFooter.vue'
import type { FavoriteListItem } from '../services/favorites'
import { useFavorites } from '../composables/useFavorites'
import { useAuth } from '../composables/useAuth'
import { registerHeaderActions, unregisterHeaderActions } from '../composables/useHeaderActions'

const router = useRouter()
const route = useRoute()
const { currentUser } = useAuth()
const {
  favoriteItems,
  favoriteTotal,
  favoritePage,
  favoriteLimit,
  favoriteLoading,
  favoriteSearch,
  fetchFavorites,
  removeFavorite,
  getFavoriteEncryptionKey,
  initFavoritesFromCache
} = useFavorites()

interface FavoritesRouteState {
  page: number
  search: string
}

interface FetchFavoritesOptions {
  page?: number
  reset?: boolean
  search?: string
}

const searchInput = ref('')
const favoritesCollapseRef = ref<Collapse | null>(null)
const expandedFavoriteItemIds = ref<string[]>([])
const hasInitializedFavoritesPage = ref(false)
const totalPages = computed(() => Math.max(1, Math.ceil(favoriteTotal.value / favoriteLimit.value)))
const hasActiveFilters = computed(() => favoriteSearch.value.trim().length > 0)
const isInitialFavoritesLoading = computed(() => !hasInitializedFavoritesPage.value || (favoriteLoading.value && favoriteItems.value.length === 0))
const resultsHeadline = computed(() => (hasActiveFilters.value ? '搜索结果' : '全部收藏'))
const emptyState = computed(() => {
  if (hasActiveFilters.value) {
    return {
      icon: 'search_off',
      title: '没有匹配的收藏',
      copy: '尝试清空搜索条件，以查看更多收藏内容。'
    }
  }

  return {
    icon: 'star_border',
    title: '还没有收藏 Paste',
    copy: '在查看 Paste 时点击收藏，之后就能从这里快速再次打开。'
  }
})
const USER_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone
const HAS_TZ_SUFFIX_RE = /(Z|[+\-]\d{2}:\d{2})$/i
const HEADER_OWNER_ID = 'favorites-page'

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

function parseRouteState(): FavoritesRouteState {
  const search = firstQueryValue(route.query.search).trim()
  const parsedPage = parsePositiveInteger(firstQueryValue(route.query.page))

  return {
    page: parsedPage ?? 1,
    search
  }
}

function syncRouteQueryFromState() {
  const desiredPage = favoritePage.value > 1 ? String(favoritePage.value) : ''
  const desiredSearch = favoriteSearch.value.trim()
  const currentPage = firstQueryValue(route.query.page).trim()
  const currentSearch = firstQueryValue(route.query.search).trim()

  if (currentPage === desiredPage && currentSearch === desiredSearch) {
    return
  }

  const nextQuery: LocationQueryRaw = {}
  if (desiredPage) {
    nextQuery.page = desiredPage
  }
  if (desiredSearch) {
    nextQuery.search = desiredSearch
  }

  void router.replace({ query: nextQuery })
}

async function fetchFavoritesAndSyncRoute(opts: FetchFavoritesOptions = {}) {
  const applied = await fetchFavorites(opts, currentUserId())
  if (!applied) return
  hasInitializedFavoritesPage.value = true
  syncRouteQueryFromState()
}

async function applyRouteQuery() {
  const state = parseRouteState()
  const searchChanged = favoriteSearch.value !== state.search
  const pageChanged = favoritePage.value !== state.page

  if (!searchChanged && !pageChanged) {
    if (searchInput.value !== state.search) {
      searchInput.value = state.search
    }
    syncRouteQueryFromState()
    return
  }

  searchInput.value = state.search
  await fetchFavoritesAndSyncRoute({
    page: state.page,
    reset: searchChanged,
    search: state.search
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
  void fetchFavoritesAndSyncRoute({ reset: true, search: searchInput.value })
}

function handleClearSearch() {
  searchInput.value = ''
  void fetchFavoritesAndSyncRoute({ reset: true, search: '' })
}

function goToPage(page: number) {
  const target = Math.min(Math.max(Math.trunc(page), 1), totalPages.value)
  if (target === favoritePage.value) return
  void fetchFavoritesAndSyncRoute({ page: target })
}

function syncExpandedFavoriteItems() {
  const value = favoritesCollapseRef.value?.value
  if (Array.isArray(value)) {
    expandedFavoriteItemIds.value = value.map((item) => String(item))
    return
  }

  expandedFavoriteItemIds.value = typeof value === 'string' && value ? [value] : []
}

function isFavoriteItemExpanded(pasteId: string): boolean {
  return expandedFavoriteItemIds.value.includes(pasteId)
}

async function handleView(item: FavoriteListItem) {
  const key = await getFavoriteEncryptionKey(item.paste_id, currentUserId())
  if (!key) {
    snackbar({ message: '缺少解密密钥，无法打开收藏', closeable: true })
    return
  }

  window.open(`/p/${item.paste_id}#${key}`, '_blank', 'noopener')
}

function handleRemove(item: FavoriteListItem) {
  dialog({
    headline: '取消收藏',
    description: `确定要取消收藏「${item.title || item.paste_id}」吗？`,
    actions: [
      { text: '保留' },
      {
        text: '取消收藏',
        onClick: async () => {
          try {
            await removeFavorite(item.paste_id, currentUserId())
            const targetPage = Math.min(favoritePage.value, totalPages.value)
            await fetchFavoritesAndSyncRoute({ page: targetPage })
            snackbar({ message: '已取消收藏' })
          } catch {
            snackbar({ message: '取消收藏失败', closeable: true })
          }
        }
      }
    ]
  })
}

onMounted(() => {
  registerHeaderActions(HEADER_OWNER_ID, [
    {
      id: 'favorites-new-paste',
      label: '新建 Paste',
      ariaLabel: '新建 Paste',
      icon: 'add',
      kind: 'icon',
      onClick: () => { void router.push('/') }
    },
    {
      id: 'favorites-history',
      label: '历史记录',
      ariaLabel: '查看历史记录',
      icon: 'history',
      kind: 'icon',
      onClick: () => { void router.push('/history') }
    }
  ])

  const userId = currentUserId()
  if (userId !== null) {
    initFavoritesFromCache(userId)
  }
  const state = parseRouteState()
  searchInput.value = state.search

  void fetchFavoritesAndSyncRoute({
    page: state.page,
    reset: true,
    search: state.search
  }).finally(() => {
    hasInitializedFavoritesPage.value = true
  })
})

onBeforeUnmount(() => {
  unregisterHeaderActions(HEADER_OWNER_ID)
})

watch(
  [() => route.query.page, () => route.query.search],
  () => {
    void applyRouteQuery()
  }
)
</script>

<style scoped>
.favorites-page {
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

.favorites-surface {
  display: grid;
  gap: 18px;
  padding: 20px;
  border-radius: 24px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.72);
  background: rgb(var(--mdui-color-surface));
}

.favorites-filters {
  background: rgb(var(--mdui-color-surface-container-low));
}

.favorites-results {
  min-height: 240px;
  gap: 0;
  padding: 0;
}

.favorites-surface-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.favorites-results-header {
  padding: 20px 20px 18px;
}

.result-header-title {
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

.favorites-list-wrapper {
  display: grid;
  gap: 16px;
}

.favorites-collapse {
  display: grid;
  gap: 10px;
}

.favorites-collapse-item {
  overflow: hidden;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.72);
  border-radius: 20px;
  background: rgb(var(--mdui-color-surface-container-low));
}

.favorites-item-header {
  padding: 16px 20px 8px;
}

.favorites-item-main {
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

.favorites-item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px 18px;
  flex-wrap: wrap;
}

.favorites-item-actions[aria-hidden='true'] {
  visibility: hidden;
  pointer-events: none;
}

.favorites-action-button {
  --mdui-button-height: 38px;
  flex: 0 0 auto;
  font-weight: 600;
}

.favorites-action-button::part(container) {
  border-radius: 999px;
}

.favorites-action-button--remove {
  color: rgb(var(--mdui-color-on-surface-variant));
}

.favorites-action-button--remove::part(container) {
  border-color: rgb(var(--mdui-color-outline) / 0.72);
  background: rgb(var(--mdui-color-surface-container-high) / 0.36);
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
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

.status-badge[data-status='published'],
.status-badge[data-status='edited'] {
  background: rgb(var(--mdui-color-primary-container));
  color: rgb(var(--mdui-color-on-primary-container));
}

@media (max-width: 768px) {
  .favorites-surface {
    padding: 18px;
  }

  .favorites-results {
    padding: 0;
  }

  .favorites-results-header {
    padding: 18px 18px 16px;
  }

  .favorites-surface-header,
  .favorites-results-header {
    flex-direction: column;
  }

  .search-field,
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
  .favorites-page {
    padding: 20px 12px;
  }

  .favorites-surface {
    padding: 16px;
    border-radius: 20px;
  }

  .favorites-results {
    padding: 0;
  }

  .favorites-results-header {
    padding: 16px 16px 14px;
  }

  .favorites-item-header {
    padding: 14px 16px 8px;
  }

  .favorites-item-actions {
    gap: 6px;
    padding: 0 16px 16px;
  }
}
</style>
