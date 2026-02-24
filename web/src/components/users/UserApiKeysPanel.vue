<template>
  <UserPanelCard title="API Keys" subtitle="用于 API 访问（创建时仅返回一次明文）">
    <template #actions>
      <mdui-button
        variant="tonal"
        :disabled="!currentUser || isLoading"
        :loading="isLoading"
        @click="load"
      >
        刷新
      </mdui-button>
      <mdui-button variant="filled" :disabled="!currentUser" @click="openCreateDialog">
        创建
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录</div>

    <div v-else>
      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && apiKeys.length === 0" class="user-panel-empty-hint">暂无 API Key</div>

      <mdui-list v-else class="user-panel-list">
        <mdui-list-item
          v-for="key in apiKeys"
          :key="key.id"
          :headline="key.name"
          :description="keyDescription(key)"
          description-line="3"
          rounded
        >
          <div slot="end-icon" class="key-actions">
            <mdui-chip variant="outlined">{{ keyPreview(key.key_preview) }}</mdui-chip>
            <mdui-chip v-if="isExpired(key.expires_at)" variant="filled">已过期</mdui-chip>
            <mdui-button-icon
              :disabled="deletingId === key.id"
              :loading="deletingId === key.id"
              @click.stop="remove(key.id, key.name)"
            >
              <mdui-icon name="delete"></mdui-icon>
            </mdui-button-icon>
          </div>
        </mdui-list-item>
      </mdui-list>
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
        <div class="created-hint">请立即复制保存（仅创建时返回一次）：</div>
        <mdui-text-field
          :value="createdKey.api_key"
          label="API Key"
          variant="outlined"
          readonly
        ></mdui-text-field>
        <div class="created-meta">预览：{{ keyPreview(createdKey.key_preview) }}</div>
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
import { computed, onMounted, ref } from 'vue'
import { confirm } from 'mdui/functions/confirm.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/chip.js'
import 'mdui/components/dialog.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/list.js'
import 'mdui/components/list-item.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import {
  createApiKey,
  deleteApiKey,
  listApiKeys,
  type ApiKeyCreateResponse,
  type ApiKeyResponse
} from '../../services/user'
import { extractErrorMessage } from '../../utils/error'
import { formatDateTime } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

const { currentUser } = useAuth()

const apiKeys = ref<ApiKeyResponse[]>([])
const isLoading = ref(false)

const createDialogRef = ref<any>(null)
const newName = ref('')
const expiresInDays = ref('')
const isCreating = ref(false)
const createdKey = ref<ApiKeyCreateResponse | null>(null)

const deletingId = ref<number | null>(null)

const canCreate = computed(() => newName.value.trim().length > 0)

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
  const d = new Date(expiresAt)
  if (Number.isNaN(d.getTime())) return false
  return d.getTime() <= Date.now()
}

function keyDescription(key: ApiKeyResponse): string {
  return [
    `创建 ${formatDateTime(key.created_at)}`,
    `最近使用 ${formatDateTime(key.last_used_at)}`,
    `最后 IP ${key.last_used_ip ?? '-'}`,
    `过期 ${formatDateTime(key.expires_at)}`
  ].join(' · ')
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
  createDialogRef.value.open = true
}

function closeCreateDialog() {
  createDialogRef.value.open = false
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

onMounted(() => {
  void load()
})
</script>

<style scoped>
.key-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.create-form {
  margin-top: 8px;
  display: grid;
  gap: 10px;
}

.created-hint {
  margin: 4px 0 10px;
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.created-meta {
  margin-top: 6px;
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.dialog-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>
