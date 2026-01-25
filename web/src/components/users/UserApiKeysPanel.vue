<template>
  <mdui-card class="panel-card">
    <div class="panel-header">
      <div>
        <div class="panel-title">API Keys</div>
        <div class="panel-subtitle">用于 API 访问（创建时仅返回一次明文）</div>
      </div>

      <div class="header-actions">
        <mdui-button
          variant="tonal"
          :disabled="!currentUser || isLoading"
          :loading="isLoading"
          @click="load"
        >
          刷新
        </mdui-button>
        <mdui-button
          variant="filled"
          :disabled="!currentUser"
          @click="openCreateDialog"
        >
          创建
        </mdui-button>
      </div>
    </div>

    <mdui-divider></mdui-divider>

    <div v-if="!currentUser" class="empty-hint">请先登录</div>

    <div v-else>
      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && apiKeys.length === 0" class="empty-hint">
        暂无 API Key
      </div>

      <mdui-list v-else class="key-list">
        <mdui-list-item
          v-for="k in apiKeys"
          :key="k.id"
          :headline="k.name"
          :description="`创建时间：${formatDate(k.created_at)}\\nID：${k.id}`"
          description-line="2"
          rounded
        >
          <div slot="end-icon" class="end-actions">
            <mdui-button-icon
              :disabled="deletingId === k.id"
              :loading="deletingId === k.id"
              @click.stop="remove(k.id, k.name)"
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
        <mdui-text-field
          v-model="newName"
          label="名称"
          placeholder="例如：Production Key"
          variant="outlined"
          clearable
          :disabled="isCreating"
        ></mdui-text-field>
      </template>

      <template v-else>
        <div class="created-hint">
          请立即复制保存（仅创建时返回一次）：
        </div>
        <mdui-text-field
          :value="createdKey.api_key"
          label="API Key"
          variant="outlined"
          readonly
        ></mdui-text-field>
      </template>

      <div slot="action" class="dialog-actions">
        <mdui-button variant="text" @click="closeCreateDialog">关闭</mdui-button>
        <mdui-button
          v-if="createdKey"
          variant="tonal"
          @click="copyCreatedKey"
        >
          复制
        </mdui-button>
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
  </mdui-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import { confirm } from 'mdui/functions/confirm.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/card.js'
import 'mdui/components/dialog.js'
import 'mdui/components/divider.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/list.js'
import 'mdui/components/list-item.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { createApiKey, deleteApiKey, listApiKeys } from '../../services/user'
import type { ApiKeyCreateResponse, ApiKeyResponse } from '../../services/user'

const { currentUser } = useAuth()

const apiKeys = ref<ApiKeyResponse[]>([])
const isLoading = ref(false)

const createDialogRef = ref<any>(null)
const newName = ref('')
const isCreating = ref(false)
const createdKey = ref<ApiKeyCreateResponse | null>(null)

const deletingId = ref<number | null>(null)

const canCreate = computed(() => newName.value.trim().length > 0)

function formatDate(raw: string): string {
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleString()
}

async function load() {
  if (!currentUser.value) return
  isLoading.value = true
  try {
    const resp = await listApiKeys()
    apiKeys.value = resp.api_keys
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '获取 API Keys 失败'
    snackbar({ message: msg, closeable: true })
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
  isCreating.value = false
  createdKey.value = null
}

async function create() {
  if (!currentUser.value) return
  if (!canCreate.value || isCreating.value) return

  isCreating.value = true
  try {
    createdKey.value = await createApiKey(newName.value)
    snackbar({ message: 'API Key 创建成功，请立即复制保存' })
    await load()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '创建失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isCreating.value = false
  }
}

async function copyCreatedKey() {
  if (!createdKey.value) return
  try {
    await navigator.clipboard.writeText(createdKey.value.api_key)
    snackbar({ message: '已复制到剪贴板' })
  } catch (e) {
    console.warn('Clipboard write failed', e)
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
    apiKeys.value = apiKeys.value.filter((k) => k.id !== keyId)
    snackbar({ message: '已删除' })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '删除失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.panel-card {
  padding: 20px;
  box-sizing: border-box;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.2;
}

.panel-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.empty-hint {
  margin: 16px 0 0;
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.key-list {
  margin-top: 8px;
}

.end-actions {
  display: flex;
  align-items: center;
}

.created-hint {
  margin: 4px 0 10px;
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.dialog-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>
