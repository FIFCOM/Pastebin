<template>
  <UserPanelCard title="Paste 管理">
    <template #actions>
      <mdui-button variant="filled" :disabled="!canAccess || isLoading" :loading="isLoading" @click="load">
        刷新
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>
    <div v-else-if="!canAccess" class="user-panel-empty-hint">仅管理员可查看。</div>

    <div v-else class="user-panel-stack">
      <div class="user-panel-section user-panel-section--soft">
        <div class="user-panel-section-header paste-toolbar-header">
          <div class="user-panel-section-heading">
            <div class="user-panel-section-eyebrow">Filter</div>
            <div class="user-panel-section-title">查找和整理 Paste</div>
            <div class="user-panel-section-copy">只展示元数据；不会展示内容、管理密钥或解密材料。</div>
          </div>
        </div>

        <div class="filters-grid">
          <mdui-text-field
            v-model="searchInput"
            class="search-input"
            label="搜索标题、Paste ID、创建者或 IP"
            variant="outlined"
            clearable
            :disabled="isLoading"
            @keydown.enter.prevent="applyFilters"
          ></mdui-text-field>

          <mdui-select
            class="filter-select"
            label="状态"
            variant="outlined"
            :value="statusFilter"
            :disabled="isLoading"
            @change="handleStatusFilterChange"
          >
            <mdui-menu-item value="all">全部</mdui-menu-item>
            <mdui-menu-item value="draft">草稿</mdui-menu-item>
            <mdui-menu-item value="published">已发布</mdui-menu-item>
            <mdui-menu-item value="edited">已编辑</mdui-menu-item>
          </mdui-select>

          <mdui-select
            class="filter-select"
            label="类型"
            variant="outlined"
            :value="typeFilter"
            :disabled="isLoading"
            @change="handleTypeFilterChange"
          >
            <mdui-menu-item value="all">全部</mdui-menu-item>
            <mdui-menu-item value="txt">TXT</mdui-menu-item>
            <mdui-menu-item value="md">Markdown</mdui-menu-item>
          </mdui-select>

          <mdui-select
            class="filter-select"
            label="加密模式"
            variant="outlined"
            :value="encryptionFilter"
            :disabled="isLoading"
            @change="handleEncryptionFilterChange"
          >
            <mdui-menu-item value="all">全部</mdui-menu-item>
            <mdui-menu-item value="client">客户端</mdui-menu-item>
            <mdui-menu-item value="server">服务端</mdui-menu-item>
          </mdui-select>

          <mdui-select
            class="filter-select"
            label="每页"
            variant="outlined"
            :value="String(size)"
            :disabled="isLoading"
            @change="handleSizeChange"
          >
            <mdui-menu-item value="10">10</mdui-menu-item>
            <mdui-menu-item value="20">20</mdui-menu-item>
            <mdui-menu-item value="50">50</mdui-menu-item>
            <mdui-menu-item value="100">100</mdui-menu-item>
          </mdui-select>

          <mdui-button class="search-trigger" variant="filled" :disabled="isLoading" @click="applyFilters">
            搜索
          </mdui-button>
        </div>
      </div>

      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && pastes.length === 0" class="user-panel-empty-state" role="status">
        <div class="user-panel-empty-state-icon" aria-hidden="true">
          <mdui-icon name="content_paste_search"></mdui-icon>
        </div>
        <div>
          <div class="user-panel-empty-state-title">
            {{ hasActiveFilters ? '没有符合条件的 Paste' : '还没有可展示的 Paste' }}
          </div>
          <div class="user-panel-empty-state-copy">
            {{ hasActiveFilters ? '尝试放宽筛选条件或清除搜索关键字后重新查询。' : '创建 Paste 后，这里会显示可管理的元数据。' }}
          </div>
        </div>
      </div>

      <div v-else-if="pastes.length > 0" class="user-panel-list-shell">
        <div class="user-panel-list-header">
          <div>
            <div class="user-panel-list-title">共 {{ total }} 条 Paste</div>
            <div class="user-panel-list-copy">展示创建归属、来源 IP 和存储元数据；删除会同步清理关联文件。</div>
          </div>
        </div>

        <div class="user-panel-row-list">
          <article v-for="paste in pastes" :key="paste.id" class="user-panel-row paste-row">
            <div class="paste-row-content">
              <div class="paste-row-top">
                <div class="paste-identity">
                  <div class="paste-title-line">
                    <div class="user-panel-row-title">{{ paste.title || '未命名 Paste' }}</div>
                    <code class="paste-title-pill">{{ paste.id }}</code>
                    <span class="paste-title-pill">{{ typeLabel(paste.type) }}</span>
                  </div>

                  <div class="paste-owner-line">
                    <span class="paste-owner-item">
                      <mdui-icon name="person"></mdui-icon>
                      {{ creatorText(paste) }}
                    </span>
                    <span class="paste-owner-item">
                      <mdui-icon name="dns"></mdui-icon>
                      {{ creatorIpText(paste) }}
                    </span>
                    <span
                      class="paste-owner-item"
                      :title="encryptionLabel(paste.encryption_mode)"
                      :aria-label="encryptionLabel(paste.encryption_mode)"
                    >
                      <mdui-icon :name="encryptionIcon(paste.encryption_mode)"></mdui-icon>
                      {{ encryptionShortLabel(paste.encryption_mode) }}
                    </span>
                  </div>
                </div>
              </div>

              <dl class="paste-detail-grid">
                <div class="paste-detail-item">
                  <dt>读取</dt>
                  <dd>{{ viewCountText(paste) }}</dd>
                </div>
                <div class="paste-detail-item">
                  <dt>文件</dt>
                  <dd>{{ paste.file_count }} 个 / {{ humanSize(paste.file_total_size) }}</dd>
                </div>
                <div class="paste-detail-item">
                  <dt>创建</dt>
                  <dd>{{ formatDateTime(paste.created_at) }}</dd>
                </div>
                <div class="paste-detail-item">
                  <dt>更新</dt>
                  <dd>{{ formatDateTime(paste.updated_at) }}</dd>
                </div>
                <div class="paste-detail-item">
                  <dt>发布</dt>
                  <dd>{{ formatDateTime(paste.published_at) }}</dd>
                </div>
                <div class="paste-detail-item">
                  <dt>过期</dt>
                  <dd>{{ expireText(paste.expire_at) }}</dd>
                </div>
              </dl>
            </div>

            <div class="user-panel-row-actions">
              <mdui-button variant="text" @click="copyPasteId(paste.id)">复制 ID</mdui-button>
              <mdui-button
                variant="text"
                :disabled="deletingId === paste.id"
                :loading="deletingId === paste.id"
                @click="removePaste(paste)"
              >
                删除
              </mdui-button>
            </div>
          </article>
        </div>
      </div>

      <PaginationFooter
        v-if="total > 0"
        :total="total"
        :page="page"
        :total-pages="totalPages"
        :loading="isLoading"
        :show-jump="true"
        @change-page="handlePageChange"
      />
    </div>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { confirm } from 'mdui/functions/confirm.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/menu-item.js'
import 'mdui/components/select.js'
import 'mdui/components/text-field.js'

import PaginationFooter from '../common/PaginationFooter.vue'
import { useAuth } from '../../composables/useAuth'
import {
  deleteAdminPaste,
  listAdminPastes,
  type AdminPasteEncryptionMode,
  type AdminPasteListItem,
  type AdminPasteStatus,
  type AdminPasteType
} from '../../services/admin'
import { extractErrorMessage } from '../../utils/error'
import { formatDateTime, humanSize } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

type StatusFilter = 'all' | AdminPasteStatus
type TypeFilter = 'all' | AdminPasteType
type EncryptionFilter = 'all' | AdminPasteEncryptionMode

interface AdminPastesRouteState {
  page: number
  size: number
  search: string
  status: StatusFilter
  type: TypeFilter
  encryptionMode: EncryptionFilter
}

const router = useRouter()
const route = useRoute()
const { currentUser } = useAuth()
const ADMIN_PASTES_TAB = 'admin-pastes'
const DEFAULT_PAGE_SIZE = 10
const PAGE_SIZE_VALUES = [10, 20, 50, 100] as const
const PASTE_LIST_QUERY_KEYS = ['page', 'size', 'search', 'role', 'status', 'type', 'encryption_mode'] as const

const pastes = ref<AdminPasteListItem[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(DEFAULT_PAGE_SIZE)
const isLoading = ref(false)
const hasLoadedFromRoute = ref(false)
const deletingId = ref<string | null>(null)

const searchInput = ref('')
const appliedSearch = ref('')
const statusFilter = ref<StatusFilter>('all')
const typeFilter = ref<TypeFilter>('all')
const encryptionFilter = ref<EncryptionFilter>('all')

const canAccess = computed(() => currentUser.value?.role === 'admin')
const isActivePanel = computed(() => firstQueryValue(route.query.tab) === ADMIN_PASTES_TAB)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))
const hasActiveFilters = computed(
  () =>
    appliedSearch.value.length > 0 ||
    statusFilter.value !== 'all' ||
    typeFilter.value !== 'all' ||
    encryptionFilter.value !== 'all'
)

function statusParam(): AdminPasteStatus | undefined {
  return statusFilter.value === 'all' ? undefined : statusFilter.value
}

function typeParam(): AdminPasteType | undefined {
  return typeFilter.value === 'all' ? undefined : typeFilter.value
}

function encryptionParam(): AdminPasteEncryptionMode | undefined {
  return encryptionFilter.value === 'all' ? undefined : encryptionFilter.value
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

function parsePageSize(value: string): number {
  const parsed = parsePositiveInteger(value)
  return parsed && (PAGE_SIZE_VALUES as readonly number[]).includes(parsed) ? parsed : DEFAULT_PAGE_SIZE
}

function parseStatusFilter(value: string): StatusFilter {
  return value === 'draft' || value === 'published' || value === 'edited' ? value : 'all'
}

function parseTypeFilter(value: string): TypeFilter {
  return value === 'txt' || value === 'md' ? value : 'all'
}

function parseEncryptionFilter(value: string): EncryptionFilter {
  return value === 'client' || value === 'server' ? value : 'all'
}

function parseRouteState(): AdminPastesRouteState {
  return {
    page: parsePositiveInteger(firstQueryValue(route.query.page)) ?? 1,
    size: parsePageSize(firstQueryValue(route.query.size)),
    search: firstQueryValue(route.query.search).trim(),
    status: parseStatusFilter(firstQueryValue(route.query.status)),
    type: parseTypeFilter(firstQueryValue(route.query.type)),
    encryptionMode: parseEncryptionFilter(firstQueryValue(route.query.encryption_mode))
  }
}

function queryValuesMatch(nextQuery: LocationQueryRaw): boolean {
  const keys = new Set([...Object.keys(route.query), ...Object.keys(nextQuery)])
  for (const key of keys) {
    if (firstQueryValue(route.query[key]) !== firstQueryValue(nextQuery[key])) {
      return false
    }
  }
  return true
}

function syncRouteQueryFromState() {
  if (!isActivePanel.value) return

  const nextQuery: LocationQueryRaw = { ...route.query }
  for (const key of PASTE_LIST_QUERY_KEYS) {
    delete nextQuery[key]
  }

  if (page.value > 1) nextQuery.page = String(page.value)
  if (size.value !== DEFAULT_PAGE_SIZE) nextQuery.size = String(size.value)
  if (appliedSearch.value.trim()) nextQuery.search = appliedSearch.value.trim()
  if (statusFilter.value !== 'all') nextQuery.status = statusFilter.value
  if (typeFilter.value !== 'all') nextQuery.type = typeFilter.value
  if (encryptionFilter.value !== 'all') nextQuery.encryption_mode = encryptionFilter.value

  if (!queryValuesMatch(nextQuery)) {
    void router.replace({ query: nextQuery })
  }
}

async function load() {
  if (!canAccess.value) {
    pastes.value = []
    total.value = 0
    hasLoadedFromRoute.value = false
    return
  }

  isLoading.value = true
  try {
    const resp = await listAdminPastes({
      page: page.value,
      size: size.value,
      search: appliedSearch.value,
      status: statusParam(),
      type: typeParam(),
      encryptionMode: encryptionParam()
    })
    pastes.value = resp.pastes
    total.value = resp.total
    page.value = resp.page
    size.value = resp.size
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取 Paste 列表失败'), closeable: true })
  } finally {
    isLoading.value = false
    hasLoadedFromRoute.value = true
  }
}

async function loadAndSyncRoute() {
  await load()
  syncRouteQueryFromState()
}

async function applyRouteQuery() {
  if (!isActivePanel.value) return

  if (!canAccess.value) {
    pastes.value = []
    total.value = 0
    hasLoadedFromRoute.value = false
    return
  }

  const state = parseRouteState()
  const hasStateChanged =
    page.value !== state.page ||
    size.value !== state.size ||
    appliedSearch.value !== state.search ||
    statusFilter.value !== state.status ||
    typeFilter.value !== state.type ||
    encryptionFilter.value !== state.encryptionMode

  if (!hasStateChanged && hasLoadedFromRoute.value) {
    if (searchInput.value !== state.search) {
      searchInput.value = state.search
    }
    syncRouteQueryFromState()
    return
  }

  page.value = state.page
  size.value = state.size
  appliedSearch.value = state.search
  searchInput.value = state.search
  statusFilter.value = state.status
  typeFilter.value = state.type
  encryptionFilter.value = state.encryptionMode
  await loadAndSyncRoute()
}

watch(totalPages, (nextTotalPages) => {
  if (!isActivePanel.value || page.value <= nextTotalPages) return
  page.value = nextTotalPages
  void loadAndSyncRoute()
})

watch(
  [
    () => route.query.tab,
    () => route.query.page,
    () => route.query.size,
    () => route.query.search,
    () => route.query.status,
    () => route.query.type,
    () => route.query.encryption_mode,
    canAccess
  ],
  () => {
    void applyRouteQuery()
  },
  { immediate: true }
)

function applyFilters() {
  appliedSearch.value = searchInput.value.trim()
  page.value = 1
  void loadAndSyncRoute()
}

function handleStatusFilterChange(event: Event) {
  const next = String((event.target as { value?: unknown }).value ?? 'all')
  if (next === 'all' || next === 'draft' || next === 'published' || next === 'edited') {
    statusFilter.value = next
    appliedSearch.value = searchInput.value.trim()
    page.value = 1
    void loadAndSyncRoute()
  }
}

function handleTypeFilterChange(event: Event) {
  const next = String((event.target as { value?: unknown }).value ?? 'all')
  if (next === 'all' || next === 'txt' || next === 'md') {
    typeFilter.value = next
    appliedSearch.value = searchInput.value.trim()
    page.value = 1
    void loadAndSyncRoute()
  }
}

function handleEncryptionFilterChange(event: Event) {
  const next = String((event.target as { value?: unknown }).value ?? 'all')
  if (next === 'all' || next === 'client' || next === 'server') {
    encryptionFilter.value = next
    appliedSearch.value = searchInput.value.trim()
    page.value = 1
    void loadAndSyncRoute()
  }
}

function handleSizeChange(event: Event) {
  const next = Number((event.target as { value?: unknown }).value)
  if (!Number.isFinite(next) || !(PAGE_SIZE_VALUES as readonly number[]).includes(next)) return
  appliedSearch.value = searchInput.value.trim()
  size.value = next
  page.value = 1
  void loadAndSyncRoute()
}

function handlePageChange(nextPage: number) {
  if (page.value === nextPage) return
  page.value = nextPage
  void loadAndSyncRoute()
}

function typeLabel(type: AdminPasteType): string {
  return type === 'md' ? 'MD' : 'TXT'
}

function encryptionLabel(mode: AdminPasteEncryptionMode): string {
  return mode === 'server' ? '服务端加密' : '客户端加密'
}

function encryptionShortLabel(mode: AdminPasteEncryptionMode): string {
  return mode === 'server' ? '服务端' : '客户端'
}

function encryptionIcon(mode: AdminPasteEncryptionMode): string {
  return mode === 'server' ? 'admin_panel_settings' : 'lock'
}

function viewCountText(paste: AdminPasteListItem): string {
  return paste.max_views === -1 ? String(paste.view_count) : `${paste.view_count} / ${paste.max_views}`
}

function creatorText(paste: AdminPasteListItem): string {
  if (paste.creator_type === 'guest') return 'Guest'
  if (paste.creator_username) {
    return paste.creator_user_id === null ? paste.creator_username : `${paste.creator_username} #${paste.creator_user_id}`
  }
  if (paste.creator_user_id !== null) return `已删除用户 #${paste.creator_user_id}`
  return '已删除用户'
}

function creatorIpText(paste: AdminPasteListItem): string {
  return paste.creator_ip ? `IP ${paste.creator_ip}` : 'IP 未记录'
}

function expireText(expireAt: string | null): string {
  return expireAt ? formatDateTime(expireAt) : '永不过期'
}

async function copyPasteId(pasteId: string) {
  try {
    await navigator.clipboard.writeText(pasteId)
    snackbar({ message: 'Paste ID 已复制' })
  } catch (error) {
    console.warn('Copy paste id failed', error)
    snackbar({ message: '复制失败，请手动复制', closeable: true })
  }
}

async function removePaste(paste: AdminPasteListItem) {
  try {
    await confirm({
      headline: '删除 Paste',
      description: `确认删除 Paste「${paste.title || paste.id}」？该操作会同步删除关联内容和文件，且不可恢复。`,
      confirmText: '删除',
      cancelText: '取消',
      closeOnEsc: true,
      closeOnOverlayClick: true
    })
  } catch {
    return
  }

  deletingId.value = paste.id
  try {
    const resp = await deleteAdminPaste(paste.id)
    snackbar({ message: resp.message })
    await load()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '删除 Paste 失败'), closeable: true })
  } finally {
    deletingId.value = null
  }
}
</script>

<style scoped>
.filters-grid {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.paste-toolbar-header {
  margin-bottom: 0;
}

.search-input {
  flex: 1 1 260px;
  min-width: 0;
}

.filter-select {
  flex: 1 1 150px;
  min-width: 0;
}

.search-trigger {
  flex: 0 0 auto;
  min-width: 108px;
  margin-inline-start: auto;
}

.paste-row {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.paste-row-content {
  min-width: 0;
}

.paste-row-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.paste-identity {
  min-width: 0;
}

.paste-title-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.paste-title-pill {
  min-height: 26px;
  min-width: 52px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 14px;
  border-radius: 999px;
  background: rgb(var(--mdui-color-surface-container-high));
  color: rgb(var(--mdui-color-on-surface-variant));
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: 0;
  white-space: nowrap;
  overflow-wrap: anywhere;
}

.paste-owner-line {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}

.paste-owner-item {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: rgb(var(--mdui-color-on-surface-variant));
  font-size: 0.84rem;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.paste-owner-item mdui-icon {
  width: 17px;
  height: 17px;
  font-size: 17px;
  color: rgb(var(--mdui-color-primary));
  flex: 0 0 auto;
}

.paste-detail-grid {
  margin: 14px 0 0;
  padding: 12px 0 0;
  border-top: 1px solid rgb(var(--mdui-color-outline-variant) / 0.7);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));
  gap: 10px 18px;
}

.paste-detail-item {
  min-width: 0;
}

.paste-detail-item dt {
  margin: 0 0 2px;
  color: rgb(var(--mdui-color-on-surface-variant));
  font-size: 0.74rem;
  line-height: 1.2;
}

.paste-detail-item dd {
  margin: 0;
  color: rgb(var(--mdui-color-on-surface));
  font-size: 0.86rem;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

@media (max-width: 960px) {
  .search-input,
  .filter-select,
  .search-trigger {
    flex-basis: 100%;
  }

  .search-trigger {
    margin-inline-start: 0;
  }

  .paste-row {
    grid-template-columns: 1fr;
  }

  .paste-row-top {
    flex-direction: column;
  }

  .paste-title-line .user-panel-row-title {
    flex: 0 0 100%;
    max-width: 100%;
  }

  .user-panel-row-actions {
    justify-content: flex-start;
  }
}
</style>
