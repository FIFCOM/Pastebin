<template>
  <mdui-card class="panel-card">
    <div class="panel-header">
      <div>
        <div class="panel-title">我的账户</div>
        <div class="panel-subtitle">查看与更新账户基本信息</div>
      </div>
      <mdui-button
        variant="tonal"
        :disabled="!currentUser || isRefreshing"
        :loading="isRefreshing"
        @click="refreshUser"
      >
        刷新
      </mdui-button>
    </div>

    <mdui-divider></mdui-divider>

    <div class="info-grid">
      <div class="info-item">
        <div class="info-label">用户 ID</div>
        <div class="info-value">{{ currentUser?.id ?? '-' }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">用户名</div>
        <div class="info-value">{{ currentUser?.username ?? '-' }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">邮箱</div>
        <div class="info-value">{{ currentUser?.email ?? '未设置' }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">创建时间</div>
        <div class="info-value">{{ formatDate(currentUser?.created_at) }}</div>
      </div>
    </div>

    <mdui-divider></mdui-divider>

    <form class="edit-form" @submit.prevent="save">
      <mdui-text-field
        v-model="newEmail"
        label="更新邮箱"
        placeholder="name@example.com"
        type="email"
        variant="outlined"
        clearable
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
  </mdui-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/card.js'
import 'mdui/components/button.js'
import 'mdui/components/divider.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { fetchCurrentUser } from '../../services/auth'
import { updateUser } from '../../services/user'

const { currentUser } = useAuth()

const isRefreshing = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')

const newEmail = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

watch(
  currentUser,
  (u) => {
    newEmail.value = u?.email ?? ''
  },
  { immediate: true }
)

const canSave = computed(() => {
  if (!currentUser.value) return false

  const nextEmail = newEmail.value.trim()
  const currentEmail = currentUser.value.email ?? ''
  const emailChanged = nextEmail !== currentEmail && nextEmail.length > 0

  const wantsPasswordChange = newPassword.value.length > 0 || confirmPassword.value.length > 0
  if (wantsPasswordChange) {
    if (!newPassword.value) return false
    if (newPassword.value !== confirmPassword.value) return false
  }

  return emailChanged || wantsPasswordChange
})

function formatDate(raw?: string): string {
  if (!raw) return '-'
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleString()
}

async function refreshUser() {
  if (!currentUser.value) return
  isRefreshing.value = true
  try {
    const user = await fetchCurrentUser()
    currentUser.value = user
    snackbar({ message: '已刷新用户信息' })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '刷新失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isRefreshing.value = false
  }
}

async function save() {
  if (!currentUser.value || isSaving.value) return
  if (!canSave.value) return

  errorMessage.value = ''

  const update: { email?: string; password?: string } = {}
  const email = newEmail.value.trim()
  if (email && email !== (currentUser.value.email ?? '')) update.email = email

  if (newPassword.value || confirmPassword.value) {
    if (!newPassword.value) {
      errorMessage.value = '新密码不能为空'
      return
    }
    if (newPassword.value !== confirmPassword.value) {
      errorMessage.value = '两次输入的新密码不一致'
      return
    }
    update.password = newPassword.value
  }

  if (!update.email && !update.password) {
    return
  }

  isSaving.value = true
  try {
    const updated = await updateUser(currentUser.value.id, update)
    currentUser.value = updated
    newPassword.value = ''
    confirmPassword.value = ''
    snackbar({ message: '已保存' })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || (e instanceof Error ? e.message : '保存失败')
    errorMessage.value = msg
    snackbar({ message: msg, closeable: true })
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.panel-card {
  padding: 20px;
  box-sizing: border-box;
}

.panel-header {
  display: flex;
  align-items: center;
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

.info-grid {
  margin: 16px 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
}

.info-item {
  min-width: 0;
}

.info-label {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.info-value {
  margin-top: 4px;
  font-size: 14px;
  word-break: break-all;
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
  .info-grid {
    grid-template-columns: 1fr;
  }

  .password-grid {
    grid-template-columns: 1fr;
  }
}
</style>
