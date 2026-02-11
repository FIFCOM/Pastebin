<template>
  <mdui-card class="panel-card">
    <div class="panel-header">
      <div>
        <div class="panel-title">用户列表</div>
        <div class="panel-subtitle">分页查看并创建用户</div>
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
          创建用户
        </mdui-button>
      </div>
    </div>

    <mdui-divider></mdui-divider>

    <div v-if="!currentUser" class="empty-hint">请先登录</div>

    <div v-else>
      <div class="toolbar">
        <div class="pager">
          <mdui-button
            variant="text"
            :disabled="page <= 1 || isLoading"
            @click="page = page - 1"
          >
            上一页
          </mdui-button>
          <div class="pager-info">
            第 {{ page }} / {{ totalPages }} 页（共 {{ total }} 条）
          </div>
          <mdui-button
            variant="text"
            :disabled="page >= totalPages || isLoading"
            @click="page = page + 1"
          >
            下一页
          </mdui-button>
        </div>

        <mdui-select
          class="size-select"
          label="每页"
          variant="outlined"
          :value="String(size)"
          @change="handleSizeChange"
        >
          <mdui-menu-item value="10">10</mdui-menu-item>
          <mdui-menu-item value="20">20</mdui-menu-item>
          <mdui-menu-item value="50">50</mdui-menu-item>
          <mdui-menu-item value="100">100</mdui-menu-item>
        </mdui-select>
      </div>

      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && users.length === 0" class="empty-hint">
        暂无用户
      </div>

      <mdui-list v-else class="user-list">
        <mdui-list-item
          v-for="u in users"
          :key="u.id"
          :headline="u.username"
          :description="`${u.email ?? '未设置邮箱'}\\n创建：${formatDate(u.created_at)}`"
          description-line="2"
          rounded
        >
          <div slot="end-icon" class="end-actions">
            <mdui-chip variant="outlined">ID {{ u.id }}</mdui-chip>
            <mdui-chip :variant="u.totp_enabled ? 'filled' : 'outlined'">
              {{ u.totp_enabled ? 'TOTP' : 'No TOTP' }}
            </mdui-chip>
          </div>
        </mdui-list-item>
      </mdui-list>
    </div>

    <mdui-dialog
      ref="createDialogRef"
      close-on-esc
      close-on-overlay-click
      @closed="resetCreateForm"
    >
      <span slot="headline">创建用户</span>
      <span slot="description">密码将以 SHA256 哈希后发送到服务端</span>

      <form class="create-form" @submit.prevent="create">
        <mdui-text-field
          v-model="createUsername"
          label="用户名（可选）"
          placeholder="留空自动生成"
          variant="outlined"
          clearable
          :disabled="isCreating"
        ></mdui-text-field>

        <mdui-text-field
          v-model="createEmail"
          label="邮箱"
          placeholder="name@example.com"
          type="email"
          variant="outlined"
          clearable
          :disabled="isCreating"
        ></mdui-text-field>

        <mdui-text-field
          v-model="createPassword"
          label="密码"
          placeholder="请输入密码"
          type="password"
          variant="outlined"
          :disabled="isCreating"
        ></mdui-text-field>

        <mdui-text-field
          v-model="createPassword2"
          label="确认密码"
          placeholder="请再次输入密码"
          type="password"
          variant="outlined"
          :disabled="isCreating"
        ></mdui-text-field>
      </form>

      <div slot="action" class="dialog-actions">
        <mdui-button variant="text" @click="closeCreateDialog">取消</mdui-button>
        <mdui-button
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
import { computed, onMounted, ref, watch } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'
import 'mdui/components/chip.js'
import 'mdui/components/dialog.js'
import 'mdui/components/divider.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/list.js'
import 'mdui/components/list-item.js'
import 'mdui/components/menu-item.js'
import 'mdui/components/select.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { createUser, listUsers } from '../../services/user'
import type { UserResponse } from '../../services/auth'

const { currentUser } = useAuth()

const users = ref<UserResponse[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const isLoading = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

function formatDate(raw: string): string {
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleString()
}

async function load() {
  if (!currentUser.value) return
  isLoading.value = true
  try {
    const resp = await listUsers(page.value, size.value)
    users.value = resp.users
    total.value = resp.total
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '获取用户列表失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isLoading.value = false
  }
}

watch([page, size], () => {
  load()
})

watch(
  totalPages,
  (tp) => {
    if (page.value > tp) page.value = tp
  },
  { immediate: true }
)

function handleSizeChange(e: Event) {
  const next = Number((e.target as any).value)
  if (!Number.isFinite(next) || next <= 0) return
  size.value = next
  page.value = 1
}

const createDialogRef = ref<any>(null)
const createUsername = ref('')
const createEmail = ref('')
const createPassword = ref('')
const createPassword2 = ref('')
const isCreating = ref(false)

const canCreate = computed(() => {
  if (!createEmail.value.trim()) return false
  if (!createPassword.value) return false
  if (createPassword.value !== createPassword2.value) return false
  return true
})

function openCreateDialog() {
  createDialogRef.value.open = true
}

function closeCreateDialog() {
  createDialogRef.value.open = false
}

function resetCreateForm() {
  createUsername.value = ''
  createEmail.value = ''
  createPassword.value = ''
  createPassword2.value = ''
  isCreating.value = false
}

async function create() {
  if (!currentUser.value) return
  if (!canCreate.value || isCreating.value) return

  isCreating.value = true
  try {
    await createUser({
      username: createUsername.value,
      email: createEmail.value,
      password: createPassword.value
    })
    snackbar({ message: '用户创建成功' })
    closeCreateDialog()
    await load()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '创建用户失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isCreating.value = false
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
  color: rgb(var(--mdui-color-on-surface-variant));
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.toolbar {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.pager {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pager-info {
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.size-select {
  min-width: 140px;
}

.empty-hint {
  margin: 16px 0 0;
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.user-list {
  margin-top: 8px;
}

.end-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.create-form {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>
