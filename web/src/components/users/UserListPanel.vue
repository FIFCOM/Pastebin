<template>
  <UserPanelCard title="用户列表">
    <template #actions>
      <mdui-button
        variant="filled"
        :disabled="!canAccess"
        @click="openCreateDialog"
      >
        创建用户
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>
    <div v-else-if="!canAccess" class="user-panel-empty-hint">仅管理员可查看。</div>

    <div v-else class="user-panel-stack">
      <div class="user-panel-section user-panel-section--soft">
        <div class="user-panel-section-header user-list-toolbar-header">
          <div class="user-panel-section-heading">
            <div class="user-panel-section-eyebrow">筛选</div>
            <div class="user-panel-section-title">查找和整理用户</div>
            <div class="user-panel-section-copy">按账号、角色、状态和分页大小过滤当前用户列表。</div>
          </div>
        </div>

        <div class="filters-grid">
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
            class="filter-select"
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
            class="filter-select"
            label="状态"
            variant="outlined"
            :value="statusFilter"
            @change="handleStatusFilterChange"
          >
            <mdui-menu-item value="all">全部</mdui-menu-item>
            <mdui-menu-item value="active">正常</mdui-menu-item>
            <mdui-menu-item value="disabled">已封禁</mdui-menu-item>
          </mdui-select>

          <mdui-select
            class="filter-select"
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

          <mdui-button
            class="search-trigger"
            variant="filled"
            :disabled="isLoading"
            @click="applyFilters"
          >
            搜索
          </mdui-button>
        </div>
      </div>

      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <div v-if="!isLoading && users.length === 0" class="user-panel-empty-state" role="status">
        <div class="user-panel-empty-state-icon" aria-hidden="true">
          <mdui-icon name="group_search"></mdui-icon>
        </div>
        <div>
          <div class="user-panel-empty-state-title">
            {{ hasActiveFilters ? '没有符合条件的用户' : '还没有可展示的用户' }}
          </div>
          <div class="user-panel-empty-state-copy">
            {{ hasActiveFilters ? '尝试放宽筛选条件或清除搜索关键字后重新查询。' : '创建首个用户后，这里会显示账号状态、角色与安全信息。' }}
          </div>
        </div>
      </div>

      <div v-else-if="users.length > 0" class="user-panel-list-shell">
        <div class="user-panel-list-header">
          <div>
            <div class="user-panel-list-title">共 {{ total }} 位用户</div>
            <div class="user-panel-list-copy">列表保留现有分页、筛选和管理操作。</div>
          </div>
        </div>

        <div class="user-panel-row-list">
          <article v-for="user in users" :key="user.id" class="user-panel-row">
            <div class="user-panel-row-main">
              <div class="user-panel-row-title-row">
                <div class="user-panel-row-title">{{ user.username }}</div>
                <mdui-chip :variant="user.role === 'admin' ? 'filled' : 'outlined'">
                  {{ user.role === 'admin' ? 'Admin' : 'User' }}
                </mdui-chip>
                <mdui-chip :variant="user.is_active ? 'tonal' : 'outlined'">
                  {{ user.is_active ? '正常' : '已封禁' }}
                </mdui-chip>
              </div>

              <div class="user-panel-row-description">{{ user.email ?? '未设置邮箱' }}</div>

              <div class="user-panel-meta">
                <span class="user-panel-meta-item">创建 {{ formatDateTime(user.created_at) }}</span>
                <span class="user-panel-meta-item">{{ user.totp_enabled ? 'TOTP 已启用' : 'TOTP 未启用' }}</span>
                <span class="user-panel-meta-item">用户 ID #{{ user.id }}</span>
              </div>
            </div>

            <div class="user-panel-row-actions">
              <mdui-button variant="text" @click="openEditDialog(user)">编辑</mdui-button>
              <mdui-button
                variant="text"
                :disabled="deletingId === user.id"
                :loading="deletingId === user.id"
                @click="removeUser(user)"
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
        @change-page="handlePageChange"
      />
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
          v-model="editUsername"
          label="用户名"
          placeholder="请输入用户名"
          variant="outlined"
          clearable
          :disabled="isSavingEdit"
        ></mdui-text-field>

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
          <mdui-menu-item value="active">正常</mdui-menu-item>
          <mdui-menu-item value="disabled">已封禁</mdui-menu-item>
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
import 'mdui/components/chip.js'
import 'mdui/components/dialog.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/menu-item.js'
import 'mdui/components/select.js'
import 'mdui/components/text-field.js'

import PaginationFooter from '../common/PaginationFooter.vue'
import { useAuth } from '../../composables/useAuth'
import { createUser, deleteUser, listUsers, updateUser } from '../../services/user'
import type { UserResponse } from '../../services/auth'
import { extractErrorMessage } from '../../utils/error'
import { formatDateTime } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

type DialogElement = HTMLElement & { open: boolean }

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
const hasActiveFilters = computed(
  () => appliedSearch.value.length > 0 || roleFilter.value !== 'all' || statusFilter.value !== 'all'
)

function handlePageChange(nextPage: number) {
  page.value = nextPage
}

function roleParam(): 'admin' | 'user' | undefined {
  if (roleFilter.value === 'all') return undefined
  return roleFilter.value
}

function statusParam(): boolean | undefined {
  if (statusFilter.value === 'all') return undefined
  return statusFilter.value === 'active'
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
    page.value = resp.page
    size.value = resp.size
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取用户列表失败'), closeable: true })
  } finally {
    isLoading.value = false
  }
}

function resetToFirstPageAndLoad() {
  if (page.value !== 1) {
    page.value = 1
    return
  }

  void load()
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
    resetToFirstPageAndLoad()
  },
  { immediate: true }
)

function applyFilters() {
  appliedSearch.value = searchInput.value.trim()
  resetToFirstPageAndLoad()
}

function handleRoleFilterChange(event: Event) {
  const next = String((event.target as { value?: unknown }).value ?? 'all')
  if (next === 'all' || next === 'admin' || next === 'user') {
    roleFilter.value = next
    appliedSearch.value = searchInput.value.trim()
    resetToFirstPageAndLoad()
  }
}

function handleStatusFilterChange(event: Event) {
  const next = String((event.target as { value?: unknown }).value ?? 'all')
  if (next === 'all' || next === 'active' || next === 'disabled') {
    statusFilter.value = next
    appliedSearch.value = searchInput.value.trim()
    resetToFirstPageAndLoad()
  }
}

function handleSizeChange(event: Event) {
  const next = Number((event.target as { value?: unknown }).value)
  if (!Number.isFinite(next) || next <= 0) return
  appliedSearch.value = searchInput.value.trim()
  size.value = next
  page.value = 1
}

const createDialogRef = ref<DialogElement | null>(null)
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
  if (createDialogRef.value) {
    createDialogRef.value.open = true
  }
}

function closeCreateDialog() {
  if (createDialogRef.value) {
    createDialogRef.value.open = false
  }
}

function resetCreateForm() {
  createUsername.value = ''
  createEmail.value = ''
  createRole.value = 'user'
  createPassword.value = ''
  createPassword2.value = ''
  isCreating.value = false
}

function handleCreateRoleChange(event: Event) {
  const next = String((event.target as { value?: unknown }).value ?? 'user')
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

const editDialogRef = ref<DialogElement | null>(null)
const editingUser = ref<UserResponse | null>(null)
const editUsername = ref('')
const editEmail = ref('')
const editPassword = ref('')
const editRole = ref<'admin' | 'user'>('user')
const editIsActive = ref(true)
const isSavingEdit = ref(false)
const deletingId = ref<number | null>(null)

const canSaveEdit = computed(() => {
  const user = editingUser.value
  if (!user) return false

  const nextUsername = editUsername.value.trim()
  if (!nextUsername) return false

  const hasUsernameChanged = nextUsername !== user.username
  const hasEmailChanged = editEmail.value.trim() !== (user.email ?? '')
  const hasPasswordChanged = editPassword.value.length > 0
  const hasRoleChanged = editRole.value !== user.role
  const hasStatusChanged = editIsActive.value !== user.is_active

  return hasUsernameChanged || hasEmailChanged || hasPasswordChanged || hasRoleChanged || hasStatusChanged
})

function openEditDialog(user: UserResponse) {
  editingUser.value = user
  editUsername.value = user.username
  editEmail.value = user.email ?? ''
  editPassword.value = ''
  editRole.value = user.role
  editIsActive.value = user.is_active
  if (editDialogRef.value) {
    editDialogRef.value.open = true
  }
}

function closeEditDialog() {
  if (editDialogRef.value) {
    editDialogRef.value.open = false
  }
}

function resetEditForm() {
  editingUser.value = null
  editUsername.value = ''
  editEmail.value = ''
  editPassword.value = ''
  editRole.value = 'user'
  editIsActive.value = true
  isSavingEdit.value = false
}

function handleEditRoleChange(event: Event) {
  const next = String((event.target as { value?: unknown }).value ?? 'user')
  if (next === 'admin' || next === 'user') {
    editRole.value = next
  }
}

function handleEditStatusChange(event: Event) {
  const next = String((event.target as { value?: unknown }).value ?? 'active')
  editIsActive.value = next === 'active'
}

async function saveEdit() {
  const user = editingUser.value
  if (!user || !canSaveEdit.value || isSavingEdit.value) return

  isSavingEdit.value = true
  try {
    const payload: {
      username?: string
      email?: string
      password?: string
      role?: 'admin' | 'user'
      is_active?: boolean
    } = {}

    const nextUsername = editUsername.value.trim()
    if (!nextUsername) {
      snackbar({ message: '用户名不能为空', closeable: true })
      return
    }
    if (nextUsername !== user.username) payload.username = nextUsername

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
.filters-grid {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.user-list-toolbar-header {
  margin-bottom: 0;
}

.search-input {
  flex: 1 1 280px;
  min-width: 0;
}

.filter-select {
  flex: 1 1 160px;
  min-width: 0;
}

.search-trigger {
  flex: 0 0 auto;
  min-width: 108px;
  margin-inline-start: auto;
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

@media (max-width: 960px) {
  .search-input,
  .filter-select,
  .search-trigger {
    flex-basis: 100%;
  }

  .search-trigger {
    margin-inline-start: 0;
  }
}
</style>
