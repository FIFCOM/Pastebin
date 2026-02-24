<template>
  <UserPanelCard title="我的账户" subtitle="查看并更新账户安全信息">
    <template #actions>
      <mdui-button
        variant="tonal"
        :disabled="!currentUser || isRefreshing"
        :loading="isRefreshing"
        @click="refreshUser"
      >
        刷新
      </mdui-button>
    </template>

    <div class="profile-overview">
      <div class="avatar" :aria-label="`用户 ${currentUser?.username ?? ''}`">{{ avatarText }}</div>
      <div class="overview-main">
        <div class="name-row">
          <div class="display-name">{{ currentUser?.username ?? '-' }}</div>
          <mdui-chip variant="outlined">{{ roleLabel }}</mdui-chip>
        </div>
        <div class="email-row">{{ currentUser?.email ?? '未设置邮箱' }}</div>
        <div class="meta-row">注册于 {{ formatDateTime(currentUser?.created_at) }}</div>
        <div class="meta-row subtle">用户 ID: {{ currentUser?.id ?? '-' }}</div>
      </div>
    </div>

    <mdui-divider></mdui-divider>

    <form class="edit-form" @submit.prevent="save">
      <mdui-text-field
        v-model="newUsername"
        label="更新用户名"
        placeholder="请输入用户名"
        variant="outlined"
        clearable
        :disabled="isSaving"
      ></mdui-text-field>

      <mdui-text-field
        v-model="newEmail"
        label="更新邮箱"
        placeholder="name@example.com"
        type="email"
        variant="outlined"
        clearable
        :disabled="isSaving"
      ></mdui-text-field>

      <mdui-text-field
        v-model="currentPassword"
        label="当前密码"
        placeholder="修改邮箱或密码时必填"
        type="password"
        variant="outlined"
        :disabled="isSaving"
      ></mdui-text-field>

      <div class="password-grid">
        <mdui-text-field
          v-model="newPassword"
          label="新密码"
          placeholder="请输入新密码"
          type="password"
          variant="outlined"
          :disabled="isSaving"
        ></mdui-text-field>
        <mdui-text-field
          v-model="confirmPassword"
          label="确认新密码"
          placeholder="请再次输入新密码"
          type="password"
          variant="outlined"
          :disabled="isSaving"
        ></mdui-text-field>
      </div>

      <div class="form-actions">
        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        <mdui-button
          type="submit"
          variant="filled"
          :disabled="!canSave || isSaving"
          :loading="isSaving"
        >
          保存修改
        </mdui-button>
      </div>
    </form>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/chip.js'
import 'mdui/components/divider.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { fetchCurrentUser } from '../../services/auth'
import { updateUser } from '../../services/user'
import { extractErrorMessage } from '../../utils/error'
import { formatDateTime } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'

const { currentUser } = useAuth()

const isRefreshing = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')

const newUsername = ref('')
const newEmail = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

watch(
  currentUser,
  (user) => {
    newUsername.value = user?.username ?? ''
    newEmail.value = user?.email ?? ''
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  },
  { immediate: true }
)

const roleLabel = computed(() => {
  if (!currentUser.value) return '-'
  return currentUser.value.role === 'admin' ? '管理员' : '普通用户'
})

const avatarText = computed(() => {
  const username = currentUser.value?.username?.trim()
  if (!username) return '?'
  return username.slice(0, 1).toUpperCase()
})

const canSave = computed(() => {
  if (!currentUser.value) return false

  const username = newUsername.value.trim()
  const currentUsername = currentUser.value.username
  const usernameChanged = username !== currentUsername
  if (usernameChanged && !username) return false

  const email = newEmail.value.trim()
  const currentEmail = currentUser.value.email ?? ''
  const emailChanged = email.length > 0 && email !== currentEmail

  const wantsPasswordChange = newPassword.value.length > 0 || confirmPassword.value.length > 0
  const needsCurrentPassword = emailChanged || wantsPasswordChange

  if (wantsPasswordChange) {
    if (!newPassword.value) return false
    if (newPassword.value !== confirmPassword.value) return false
  }

  if (!usernameChanged && !emailChanged && !wantsPasswordChange) return false
  if (needsCurrentPassword) {
    return currentPassword.value.trim().length > 0
  }
  return true
})

async function refreshUser() {
  if (!currentUser.value) return

  isRefreshing.value = true
  try {
    currentUser.value = await fetchCurrentUser()
    snackbar({ message: '已刷新用户信息' })
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '刷新失败'), closeable: true })
  } finally {
    isRefreshing.value = false
  }
}

async function save() {
  if (!currentUser.value || isSaving.value || !canSave.value) return

  errorMessage.value = ''

  const username = newUsername.value.trim()
  const email = newEmail.value.trim()
  const payload: {
    username?: string
    email?: string
    password?: string
    current_password?: string
  } = {}

  if (username !== currentUser.value.username) {
    if (!username) {
      errorMessage.value = '用户名不能为空'
      return
    }
    payload.username = username
  }

  if (email && email !== (currentUser.value.email ?? '')) {
    payload.email = email
  }

  if (newPassword.value || confirmPassword.value) {
    if (!newPassword.value) {
      errorMessage.value = '新密码不能为空'
      return
    }
    if (newPassword.value !== confirmPassword.value) {
      errorMessage.value = '两次输入的新密码不一致'
      return
    }
    payload.password = newPassword.value
  }

  if (!payload.username && !payload.email && !payload.password) {
    return
  }

  if (payload.email || payload.password) {
    const currentPasswordValue = currentPassword.value.trim()
    if (!currentPasswordValue) {
      errorMessage.value = '修改邮箱或密码时需要输入当前密码'
      return
    }
    payload.current_password = currentPasswordValue
  }

  isSaving.value = true
  try {
    const updated = await updateUser(currentUser.value.id, payload)
    currentUser.value = updated
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    snackbar({ message: '已保存' })
  } catch (error: unknown) {
    const msg = extractErrorMessage(error, '保存失败')
    errorMessage.value = msg
    snackbar({ message: msg, closeable: true })
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.profile-overview {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 22px;
  font-weight: 700;
  color: rgb(var(--mdui-color-on-primary));
  background: rgb(var(--mdui-color-primary));
  flex-shrink: 0;
}

.overview-main {
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.display-name {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.2;
}

.email-row {
  margin-top: 4px;
  font-size: 14px;
  word-break: break-all;
}

.meta-row {
  margin-top: 2px;
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.meta-row.subtle {
  opacity: 0.75;
}

.edit-form {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.password-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.error-message {
  font-size: 13px;
  color: rgb(var(--mdui-color-error));
}

@media (max-width: 640px) {
  .password-grid {
    grid-template-columns: 1fr;
  }

  .profile-overview {
    align-items: flex-start;
  }
}
</style>
