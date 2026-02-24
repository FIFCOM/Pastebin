<template>
  <UserPanelCard title="用户列表" subtitle="管理员可搜索、编辑、禁用或删除用户">
    <template #actions>
      <mdui-button
        variant="tonal"
        :disabled="!canAccess || isLoading"
        :loading="isLoading"
        @click="load"
      >
        刷新
      </mdui-button>
      <mdui-button variant="filled" :disabled="!canAccess" @click="openCreateDialog">
        创建用户
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录</div>
    <div v-else-if="!canAccess" class="user-panel-empty-hint">仅管理员可查看用户列表</div>

    <div v-else>
      <div class="toolbar">
        <mdui-text-field
          v-model="searchInput"
          class="search-input"
          label="搜索用户名或邮箱"
          variant="outlined"
          clearable
          :disabled="isLoading"
          @keydown.enter.prevent="applyFilters"
        ></mdui-text-field>

        <mdui-select
          class="role-filter"
          label="角色"
          variant="outlined"
          :value="roleFilter"
          @change="handleRoleFilterChange"
        >
          <mdui-menu-item value="all">全部</mdui-menu-item>
          <mdui-menu-item value="admin">管理员</mdui-menu-item>
          <mdui-menu-item value="user">普通用户</mdui-menu-item>
        </mdui-select>

        <mdui-select
          class="status-filter"
          label="状态"
          variant="outlined"
          :value="statusFilter"
          @change="handleStatusFilterChange"
        >
          <mdui-menu-item value="all">全部</mdui-menu-item>
          <mdui-menu-item value="active">可登录</mdui-menu-item>
          <mdui-menu-item value="disabled">已禁用</mdui-menu-item>
        </mdui-select>

        <mdui-button variant="filled" :disabled="isLoading" @click="applyFilters">筛选</mdui-button>
      </div>

      <div class="toolbar pager-toolbar">
        <div class="pager">
          <mdui-button variant="text" :disabled="page <= 1 || isLoading" @click="page = page - 1">
            上一页
          </mdui-button>
          <div class="pager-info">第 {{ page }} / {{ totalPages }} 页（共 {{ total }} 条）</div>
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

      <div v-if="!isLoading && users.length === 0" class="user-panel-empty-hint">暂无用户</div>

      <mdui-list v-else class="user-panel-list">
        <mdui-list-item
          v-for="user in users"
          :key="user.id"
          :headline="user.username"
          :description="userDescription(user)"
          description-line="2"
          rounded
        >
          <div slot="end-icon" class="user-actions">
            <mdui-chip :variant="user.role === 'admin' ? 'filled' : 'outlined'">
              {{ user.role === 'admin' ? 'Admin' : 'User' }}
            </mdui-chip>
            <mdui-chip :variant="user.is_active ? 'tonal' : 'outlined'">
              {{ user.is_active ? '可登录' : '已禁用' }}
            </mdui-chip>
            <mdui-button-icon @click.stop="openEditDialog(user)">
              <mdui-icon name="edit"></mdui-icon>
            </mdui-button-icon>
            <mdui-button-icon
              :disabled="deletingId === user.id"
              :loading="deletingId === user.id"
              @click.stop="removeUser(user)"
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
      @closed="resetCreateForm"
    >
      <span slot="headline">创建用户</span>

      <form class="dialog-form" @submit.prevent="create">
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

        <mdui-select
          label="角色"
          variant="outlined"
          :value="createRole"
          :disabled="isCreating"
          @change="handleCreateRoleChange"
        >
          <mdui-menu-item value="user">普通用户</mdui-menu-item>
          <mdui-menu-item value="admin">管理员</mdui-menu-item>
        </mdui-select>

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

    <mdui-dialog
      ref="editDialogRef"
      close-on-esc
      close-on-overlay-click
      @closed="resetEditForm"
    >
      <span slot="headline">编辑用户</span>

      <form class="dialog-form" @submit.prevent="saveEdit">
        <mdui-text-field
          v-model="editEmail"
          label="邮箱"
          placeholder="name@example.com"
          type="email"
          variant="outlined"
          clearable
          :disabled="isSavingEdit"
        ></mdui-text-field>

        <mdui-text-field
          v-model="editPassword"
          label="重置密码（可选）"
          placeholder="留空表示不修改"
          type="password"
          variant="outlined"
          :disabled="isSavingEdit"
        ></mdui-text-field>

        <mdui-select
          label="角色"
          variant="outlined"
          :value="editRole"
          :disabled="isSavingEdit"
          @change="handleEditRoleChange"
        >
          <mdui-menu-item value="user">普通用户</mdui-menu-item>
          <mdui-menu-item value="admin">管理员</mdui-menu-item>
        </mdui-select>

        <mdui-select
          label="状态"
          variant="outlined"
          :value="editIsActive ? 'active' : 'disabled'"
          :disabled="isSavingEdit"
          @change="handleEditStatusChange"
        >
          <mdui-menu-item value="active">可登录</mdui-menu-item>
          <mdui-menu-item value="disabled">已禁用</mdui-menu-item>
        </mdui-select>
      </form>

      <div slot="action" class="dialog-actions">
        <mdui-button variant="text" @click="closeEditDialog">取消</mdui-button>
        <mdui-button
          variant="filled"
          :disabled="!canSaveEdit || isSavingEdit"
          :loading="isSavingEdit"
          @click="saveEdit"
        >
          保存
        </mdui-button>
      </div>
    </mdui-dialog>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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
import 'mdui/components/menu-item.js'
import 'mdui/components/select.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { createUser, deleteUser, listUsers, updateUser } from '../../services/user'
import type { UserResponse } from '../../services/auth'
import { extractErrorMessage } from '../../utils/error'
import { formatDateTime } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

const { currentUser } = useAuth()

const users = ref<UserResponse[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const isLoading = ref(false)

const searchInput = ref('')
const appliedSearch = ref('')
const roleFilter = ref<'all' | 'admin' | 'user'>('all')
const statusFilter = ref<'all' | 'active' | 'disabled'>('all')

const canAccess = computed(() => currentUser.value?.role === 'admin')
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

function roleParam(): 'admin' | 'user' | undefined {
  if (roleFilter.value === 'all') return undefined
  return roleFilter.value
}

function statusParam(): boolean | undefined {
  if (statusFilter.value === 'all') return undefined
  return statusFilter.value === 'active'
}

function userDescription(user: UserResponse): string {
  return [
    user.email ?? '未设置邮箱',
    `创建 ${formatDateTime(user.created_at)}`,
    user.totp_enabled ? 'TOTP 已启用' : 'TOTP 未启用'
  ].join(' · ')
}

async function load() {
  if (!canAccess.value) {
    users.value = []
    total.value = 0
    return
  }

  isLoading.value = true
  try {
    const resp = await listUsers({
      page: page.value,
      size: size.value,
      search: appliedSearch.value,
      role: roleParam(),
      isActive: statusParam()
    })
    users.value = resp.users
    total.value = resp.total
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取用户列表失败'), closeable: true })
  } finally {
    isLoading.value = false
  }
}

watch([page, size], () => {
  void load()
})

watch(
  totalPages,
  (nextTotalPages) => {
    if (page.value > nextTotalPages) page.value = nextTotalPages
  },
  { immediate: true }
)

watch(
  canAccess,
  () => {
    page.value = 1
    void load()
  },
  { immediate: true }
)

function applyFilters() {
  appliedSearch.value = searchInput.value.trim()
  page.value = 1
  void load()
}

function handleRoleFilterChange(e: Event) {
  const next = String((e.target as { value?: unknown }).value ?? 'all')
  if (next === 'all' || next === 'admin' || next === 'user') {
    roleFilter.value = next
    page.value = 1
    void load()
  }
}

function handleStatusFilterChange(e: Event) {
  const next = String((e.target as { value?: unknown }).value ?? 'all')
  if (next === 'all' || next === 'active' || next === 'disabled') {
    statusFilter.value = next
    page.value = 1
    void load()
  }
}

function handleSizeChange(e: Event) {
  const next = Number((e.target as { value?: unknown }).value)
  if (!Number.isFinite(next) || next <= 0) return
  size.value = next
  page.value = 1
}

const createDialogRef = ref<any>(null)
const createUsername = ref('')
const createEmail = ref('')
const createRole = ref<'admin' | 'user'>('user')
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
  createRole.value = 'user'
  createPassword.value = ''
  createPassword2.value = ''
  isCreating.value = false
}

function handleCreateRoleChange(e: Event) {
  const next = String((e.target as { value?: unknown }).value ?? 'user')
  if (next === 'admin' || next === 'user') {
    createRole.value = next
  }
}

async function create() {
  if (!canAccess.value || !canCreate.value || isCreating.value) return

  isCreating.value = true
  try {
    await createUser({
      username: createUsername.value,
      email: createEmail.value,
      password: createPassword.value,
      role: createRole.value
    })
    snackbar({ message: '用户创建成功' })
    closeCreateDialog()
    await load()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '创建用户失败'), closeable: true })
  } finally {
    isCreating.value = false
  }
}

const editDialogRef = ref<any>(null)
const editingUser = ref<UserResponse | null>(null)
const editEmail = ref('')
const editPassword = ref('')
const editRole = ref<'admin' | 'user'>('user')
const editIsActive = ref(true)
const isSavingEdit = ref(false)
const deletingId = ref<number | null>(null)

const canSaveEdit = computed(() => {
  const user = editingUser.value
  if (!user) return false

  const hasEmailChanged = editEmail.value.trim() !== (user.email ?? '')
  const hasPasswordChanged = editPassword.value.length > 0
  const hasRoleChanged = editRole.value !== user.role
  const hasStatusChanged = editIsActive.value !== user.is_active

  return hasEmailChanged || hasPasswordChanged || hasRoleChanged || hasStatusChanged
})

function openEditDialog(user: UserResponse) {
  editingUser.value = user
  editEmail.value = user.email ?? ''
  editPassword.value = ''
  editRole.value = user.role
  editIsActive.value = user.is_active
  editDialogRef.value.open = true
}

function closeEditDialog() {
  editDialogRef.value.open = false
}

function resetEditForm() {
  editingUser.value = null
  editEmail.value = ''
  editPassword.value = ''
  editRole.value = 'user'
  editIsActive.value = true
  isSavingEdit.value = false
}

function handleEditRoleChange(e: Event) {
  const next = String((e.target as { value?: unknown }).value ?? 'user')
  if (next === 'admin' || next === 'user') {
    editRole.value = next
  }
}

function handleEditStatusChange(e: Event) {
  const next = String((e.target as { value?: unknown }).value ?? 'active')
  editIsActive.value = next === 'active'
}

async function saveEdit() {
  const user = editingUser.value
  if (!user || !canSaveEdit.value || isSavingEdit.value) return

  isSavingEdit.value = true
  try {
    const payload: {
      email?: string
      password?: string
      role?: 'admin' | 'user'
      is_active?: boolean
    } = {}

    const nextEmail = editEmail.value.trim()
    if (nextEmail !== (user.email ?? '')) payload.email = nextEmail
    if (editPassword.value) payload.password = editPassword.value
    if (editRole.value !== user.role) payload.role = editRole.value
    if (editIsActive.value !== user.is_active) payload.is_active = editIsActive.value

    await updateUser(user.id, payload)
    snackbar({ message: '用户信息已更新' })
    closeEditDialog()
    await load()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '更新用户失败'), closeable: true })
  } finally {
    isSavingEdit.value = false
  }
}

async function removeUser(user: UserResponse) {
  if (!canAccess.value) return

  try {
    await confirm({
      headline: '删除用户',
      description: `确认删除用户「${user.username}」？该操作不可恢复。`,
      confirmText: '删除',
      cancelText: '取消',
      closeOnEsc: true,
      closeOnOverlayClick: true
    })
  } catch {
    return
  }

  deletingId.value = user.id
  try {
    await deleteUser(user.id)
    snackbar({ message: '用户已删除' })
    await load()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '删除用户失败'), closeable: true })
  } finally {
    deletingId.value = null
  }
}

</script>

<style scoped>
.toolbar {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-input {
  min-width: 260px;
  flex: 1 1 280px;
}

.role-filter,
.status-filter,
.size-select {
  min-width: 140px;
}

.pager-toolbar {
  justify-content: space-between;
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

.user-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.dialog-form {
  margin-top: 8px;
  display: grid;
  gap: 12px;
}

.dialog-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>
