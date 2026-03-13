<template>
  <UserPanelCard title="API Keys">
    <template #actions>
      <mdui-button variant="filled" :disabled="!currentUser" @click="openCreateDialog">创建 Key</mdui-button>
      <mdui-button
        variant="text"
        :disabled="!currentUser || expiredCount === 0 || isCleaningExpired"
        :loading="isCleaningExpired"
        @click="cleanupExpired"
      >
        清理过期 Key
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>

    <div v-else class="user-panel-stack">
      <div class="user-panel-summary-grid">
        <div class="user-panel-stat">
          <div class="user-panel-stat-label">可用 Key</div>
          <div class="user-panel-stat-value">{{ activeCount }}</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">已过期</div>
          <div class="user-panel-stat-value">{{ expiredCount }}</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">从未使用</div>
          <div class="user-panel-stat-value">{{ neverUsedCount }}</div>
        </div>
      </div>

      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && pagedApiKeys.length === 0" class="user-panel-empty-hint">暂无 API Key。</div>

      <div v-else class="user-panel-row-list">
        <article v-for="key in pagedApiKeys" :key="key.id" class="user-panel-row">
          <div class="user-panel-row-main">
            <div class="user-panel-row-title-row">
              <div class="user-panel-row-title">{{ key.name }}</div>
              <mdui-chip v-if="isExpired(key.expires_at)" variant="filled">已过期</mdui-chip>
            </div>

            <div class="api-key-preview-text">{{ keyPreview(key.key_preview) }}</div>

            <div class="user-panel-meta">
              <span class="user-panel-meta-item">创建于 {{ formatDate(key.created_at) }}</span>
              <span class="user-panel-meta-item">最后使用 {{ key.last_used_at ? formatDate(key.last_used_at) : '尚未使用' }}</span>
              <span class="user-panel-meta-item">最后使用 IP {{ key.last_used_ip ?? '-' }}</span>
              <span class="user-panel-meta-item">{{ expiresText(key.expires_at) }}</span>
            </div>
          </div>

          <div class="user-panel-row-actions">
            <mdui-button
              variant="text"
              :disabled="deletingId === key.id"
              :loading="deletingId === key.id"
              @click="remove(key.id, key.name)"
            >
              删除
            </mdui-button>
          </div>
        </article>
      </div>

      <PaginationFooter
        v-if="apiKeys.length > 0"
        :total="apiKeys.length"
        :page="page"
        :total-pages="totalPages"
        :loading="isLoading || isCleaningExpired"
        @change-page="handlePageChange"
      />
    </div>

    <mdui-dialog
      ref="createDialogRef"
      close-on-esc
      close-on-overlay-click
      @closed="resetCreateDialog"
    >
      <span slot="headline">创建 API Key</span>

      <template v-if="!createdKey">
        <div class="create-form">
          <mdui-text-field
            v-model="newName"
            label="名称"
            placeholder="例如：Production Key"
            variant="outlined"
            clearable
            :disabled="isCreating"
          ></mdui-text-field>

          <mdui-text-field
            v-model="expiresInDays"
            label="有效期（天，可选）"
            placeholder="留空表示不过期"
            variant="outlined"
            type="number"
            min="1"
            max="3650"
            :disabled="isCreating"
          ></mdui-text-field>
        </div>
      </template>

      <template v-else>
        <div class="created-state">
          <div class="created-hint">请立即复制保存，这个值之后不会再展示。</div>
          <mdui-text-field
            :value="createdKey.api_key"
            label="API Key"
            variant="outlined"
            readonly
          ></mdui-text-field>
          <div class="created-meta">预览：{{ keyPreview(createdKey.key_preview) }}</div>
        </div>
      </template>

      <div slot="action" class="dialog-actions">
        <mdui-button variant="text" @click="closeCreateDialog">关闭</mdui-button>
        <mdui-button v-if="createdKey" variant="tonal" @click="copyCreatedKey">复制</mdui-button>
        <mdui-button
          v-else
          variant="filled"
          :disabled="!canCreate || isCreating"
          :loading="isCreating"
          @click="create"
        >
          创建
        </mdui-button>
      </div>
    </mdui-dialog>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { confirm } from 'mdui/functions/confirm.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/chip.js'
import 'mdui/components/dialog.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/text-field.js'

import PaginationFooter from '../common/PaginationFooter.vue'
import { useAuth } from '../../composables/useAuth'
import {
  cleanupExpiredApiKeys,
  createApiKey,
  deleteApiKey,
  listApiKeys,
  type ApiKeyCreateResponse,
  type ApiKeyResponse
} from '../../services/user'
import { extractErrorMessage } from '../../utils/error'
import { formatDate } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

type DialogElement = HTMLElement & { open: boolean }

const PAGE_SIZE = 8

const { currentUser } = useAuth()

const apiKeys = ref<ApiKeyResponse[]>([])
const isLoading = ref(false)
const isCleaningExpired = ref(false)
const page = ref(1)

const createDialogRef = ref<DialogElement | null>(null)
const newName = ref('')
const expiresInDays = ref('')
const isCreating = ref(false)
const createdKey = ref<ApiKeyCreateResponse | null>(null)

const deletingId = ref<number | null>(null)

const canCreate = computed(() => newName.value.trim().length > 0)
const expiredCount = computed(() => apiKeys.value.filter((key) => isExpired(key.expires_at)).length)
const activeCount = computed(() => apiKeys.value.length - expiredCount.value)
const neverUsedCount = computed(() => apiKeys.value.filter((key) => !key.last_used_at).length)
const totalPages = computed(() => Math.max(1, Math.ceil(apiKeys.value.length / PAGE_SIZE)))
const pagedApiKeys = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return apiKeys.value.slice(start, start + PAGE_SIZE)
})

watch(totalPages, (nextTotalPages) => {
  if (page.value > nextTotalPages) {
    page.value = nextTotalPages
  }
})

function handlePageChange(nextPage: number) {
  page.value = nextPage
}

function keyPreview(preview: string | null | undefined): string {
  return preview?.trim() || '-'
}

function parseExpiresInDays(): number | null {
  const raw = expiresInDays.value.trim()
  if (!raw) return null
  const value = Number(raw)
  if (!Number.isFinite(value) || value <= 0) return null
  return Math.min(3650, Math.floor(value))
}

function isExpired(expiresAt: string | null): boolean {
  if (!expiresAt) return false
  const date = new Date(expiresAt)
  if (Number.isNaN(date.getTime())) return false
  return date.getTime() <= Date.now()
}

function expiresText(expiresAt: string | null): string {
  if (!expiresAt) return '永不过期'
  return `将于 ${formatDate(expiresAt)} 过期`
}

async function load() {
  if (!currentUser.value) return

  isLoading.value = true
  try {
    const resp = await listApiKeys()
    apiKeys.value = resp.api_keys
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取 API Keys 失败'), closeable: true })
  } finally {
    isLoading.value = false
  }
}

function openCreateDialog() {
  if (createDialogRef.value) {
    createDialogRef.value.open = true
  }
}

function closeCreateDialog() {
  if (createDialogRef.value) {
    createDialogRef.value.open = false
  }
}

function resetCreateDialog() {
  newName.value = ''
  expiresInDays.value = ''
  isCreating.value = false
  createdKey.value = null
}

async function create() {
  if (!currentUser.value || !canCreate.value || isCreating.value) return

  isCreating.value = true
  try {
    createdKey.value = await createApiKey(newName.value, {
      expiresInDays: parseExpiresInDays()
    })
    snackbar({ message: 'API Key 创建成功，请立即复制保存' })
    await load()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '创建失败'), closeable: true })
  } finally {
    isCreating.value = false
  }
}

async function copyCreatedKey() {
  if (!createdKey.value) return

  try {
    await navigator.clipboard.writeText(createdKey.value.api_key)
    snackbar({ message: '已复制到剪贴板' })
  } catch (error: unknown) {
    console.warn('Clipboard write failed', error)
    snackbar({ message: '复制失败，请手动复制', closeable: true })
  }
}

async function remove(keyId: number, name: string) {
  if (!currentUser.value) return

  try {
    await confirm({
      headline: '删除 API Key',
      description: `确认删除「${name}」？删除后该 Key 将立即失效。`,
      confirmText: '删除',
      cancelText: '取消',
      closeOnEsc: true,
      closeOnOverlayClick: true
    })
  } catch {
    return
  }

  deletingId.value = keyId
  try {
    await deleteApiKey(keyId)
    snackbar({ message: '已删除' })
    await load()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '删除失败'), closeable: true })
  } finally {
    deletingId.value = null
  }
}

async function cleanupExpired() {
  if (!currentUser.value || expiredCount.value === 0) return

  isCleaningExpired.value = true
  try {
    const resp = await cleanupExpiredApiKeys()
    snackbar({ message: resp.message })
    await load()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '清理失败'), closeable: true })
  } finally {
    isCleaningExpired.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.api-key-preview-text {
  margin-top: 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.9rem;
  color: rgb(var(--mdui-color-on-surface-variant));
  word-break: break-all;
}

.create-form,
.created-state {
  margin-top: 8px;
  display: grid;
  gap: 12px;
}

.created-hint,
.created-meta {
  font-size: 0.9rem;
  line-height: 1.5;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.dialog-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>
