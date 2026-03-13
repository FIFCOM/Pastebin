<template>
  <UserPanelCard title="我的账户">
    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>

    <div v-else class="user-panel-stack">
      <section class="profile-hero">
        <div class="profile-avatar" :aria-label="`用户 ${currentUser.username}`">{{ avatarText }}</div>

        <div class="profile-summary">
          <div class="profile-field-row">
            <div class="profile-name">{{ currentUser.username }}</div>
            <mdui-button-icon icon="edit" @click="openUsernameDialog"></mdui-button-icon>
          </div>

          <div class="profile-field-row profile-field-row--email">
            <div class="profile-email">{{ currentUser.email ?? '未设置邮箱' }}</div>
            <mdui-button-icon icon="edit" @click="openEmailDialog"></mdui-button-icon>
          </div>
        </div>
      </section>

      <div class="user-panel-summary-grid">
        <div class="user-panel-stat">
          <div class="user-panel-stat-label">注册时间</div>
          <div class="user-panel-stat-value profile-stat-value">{{ formatDateTime(currentUser.created_at) }}</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">账户角色</div>
          <div class="user-panel-stat-value profile-stat-value">{{ roleLabel }}</div>
        </div>

        <div class="user-panel-stat">
          <div class="user-panel-stat-label">用户 ID</div>
          <div class="user-panel-stat-value profile-stat-value profile-stat-value--mono">#{{ currentUser.id }}</div>
        </div>
      </div>

      <section class="user-panel-section">
        <div class="user-panel-section-header">
          <div>
            <div class="user-panel-section-title">修改密码</div>
          </div>
        </div>

        <form class="edit-form" @submit.prevent="savePassword">
          <mdui-text-field
            v-model="currentPassword"
            label="当前密码"
            placeholder="输入当前密码"
            type="password"
            variant="outlined"
            :disabled="isSavingPassword"
          ></mdui-text-field>

          <div class="password-grid">
            <mdui-text-field
              v-model="newPassword"
              label="新密码"
              placeholder="请输入新密码"
              type="password"
              variant="outlined"
              :disabled="isSavingPassword"
            ></mdui-text-field>

            <mdui-text-field
              v-model="confirmPassword"
              label="确认新密码"
              placeholder="请再次输入新密码"
              type="password"
              variant="outlined"
              :disabled="isSavingPassword"
            ></mdui-text-field>
          </div>

          <div class="form-footer">
            <div v-if="passwordErrorMessage" class="error-message">{{ passwordErrorMessage }}</div>

            <mdui-button
              type="submit"
              variant="filled"
              :disabled="!canSavePassword || isSavingPassword"
              :loading="isSavingPassword"
            >
              保存密码
            </mdui-button>
          </div>
        </form>
      </section>
    </div>

    <mdui-dialog ref="usernameDialogRef" close-on-esc close-on-overlay-click @closed="resetUsernameDialog">
      <span slot="headline">修改用户名</span>

      <div class="dialog-form">
        <mdui-text-field
          v-model="usernameDraft"
          label="用户名"
          placeholder="请输入用户名"
          variant="outlined"
          clearable
          :disabled="isSavingUsername"
        ></mdui-text-field>

        <div v-if="usernameErrorMessage" class="error-message">{{ usernameErrorMessage }}</div>
      </div>

      <div slot="action" class="dialog-actions">
        <mdui-button variant="text" @click="closeUsernameDialog">取消</mdui-button>
        <mdui-button
          variant="filled"
          :disabled="!canSaveUsername || isSavingUsername"
          :loading="isSavingUsername"
          @click="saveUsername"
        >
          保存
        </mdui-button>
      </div>
    </mdui-dialog>

    <mdui-dialog ref="emailDialogRef" close-on-esc close-on-overlay-click @closed="resetEmailDialog">
      <span slot="headline">修改邮箱</span>

      <div class="dialog-form">
        <mdui-text-field
          v-model="emailDraft"
          label="邮箱"
          placeholder="name@example.com"
          type="email"
          variant="outlined"
          clearable
          :disabled="isSavingEmail"
        ></mdui-text-field>

        <mdui-text-field
          v-model="emailCurrentPassword"
          label="当前密码"
          placeholder="修改邮箱时必填"
          type="password"
          variant="outlined"
          :disabled="isSavingEmail"
        ></mdui-text-field>

        <div v-if="emailErrorMessage" class="error-message">{{ emailErrorMessage }}</div>
      </div>

      <div slot="action" class="dialog-actions">
        <mdui-button variant="text" @click="closeEmailDialog">取消</mdui-button>
        <mdui-button
          variant="filled"
          :disabled="!canSaveEmail || isSavingEmail"
          :loading="isSavingEmail"
          @click="saveEmail"
        >
          保存
        </mdui-button>
      </div>
    </mdui-dialog>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/dialog.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { updateUser } from '../../services/user'
import { extractErrorMessage } from '../../utils/error'
import { formatDateTime } from '../../utils/format'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

type DialogElement = HTMLElement & { open: boolean }

const { currentUser } = useAuth()

const isSavingPassword = ref(false)
const passwordErrorMessage = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

const usernameDialogRef = ref<DialogElement | null>(null)
const usernameDraft = ref('')
const usernameErrorMessage = ref('')
const isSavingUsername = ref(false)

const emailDialogRef = ref<DialogElement | null>(null)
const emailDraft = ref('')
const emailCurrentPassword = ref('')
const emailErrorMessage = ref('')
const isSavingEmail = ref(false)

watch(
  currentUser,
  (user) => {
    usernameDraft.value = user?.username ?? ''
    emailDraft.value = user?.email ?? ''
    emailCurrentPassword.value = ''
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

const canSavePassword = computed(() => {
  if (!currentPassword.value.trim()) return false
  if (!newPassword.value) return false
  if (newPassword.value !== confirmPassword.value) return false
  return true
})

const canSaveUsername = computed(() => {
  const username = usernameDraft.value.trim()
  return Boolean(currentUser.value && username && username !== currentUser.value.username)
})

const canSaveEmail = computed(() => {
  const email = emailDraft.value.trim()
  return Boolean(
    currentUser.value &&
      email &&
      email !== (currentUser.value.email ?? '') &&
      emailCurrentPassword.value.trim()
  )
})

function openUsernameDialog() {
  if (!currentUser.value) return
  usernameDraft.value = currentUser.value.username
  usernameErrorMessage.value = ''
  if (usernameDialogRef.value) {
    usernameDialogRef.value.open = true
  }
}

function closeUsernameDialog() {
  if (usernameDialogRef.value) {
    usernameDialogRef.value.open = false
  }
}

function resetUsernameDialog() {
  usernameErrorMessage.value = ''
  isSavingUsername.value = false
  usernameDraft.value = currentUser.value?.username ?? ''
}

function openEmailDialog() {
  if (!currentUser.value) return
  emailDraft.value = currentUser.value.email ?? ''
  emailCurrentPassword.value = ''
  emailErrorMessage.value = ''
  if (emailDialogRef.value) {
    emailDialogRef.value.open = true
  }
}

function closeEmailDialog() {
  if (emailDialogRef.value) {
    emailDialogRef.value.open = false
  }
}

function resetEmailDialog() {
  emailErrorMessage.value = ''
  isSavingEmail.value = false
  emailDraft.value = currentUser.value?.email ?? ''
  emailCurrentPassword.value = ''
}

async function saveUsername() {
  if (!currentUser.value || !canSaveUsername.value || isSavingUsername.value) return

  isSavingUsername.value = true
  usernameErrorMessage.value = ''
  try {
    const updated = await updateUser(currentUser.value.id, {
      username: usernameDraft.value.trim()
    })
    currentUser.value = updated
    snackbar({ message: '用户名已更新' })
    closeUsernameDialog()
  } catch (error: unknown) {
    usernameErrorMessage.value = extractErrorMessage(error, '保存失败')
  } finally {
    isSavingUsername.value = false
  }
}

async function saveEmail() {
  if (!currentUser.value || !canSaveEmail.value || isSavingEmail.value) return

  isSavingEmail.value = true
  emailErrorMessage.value = ''
  try {
    const updated = await updateUser(currentUser.value.id, {
      email: emailDraft.value.trim(),
      current_password: emailCurrentPassword.value.trim()
    })
    currentUser.value = updated
    snackbar({ message: '邮箱已更新' })
    closeEmailDialog()
  } catch (error: unknown) {
    emailErrorMessage.value = extractErrorMessage(error, '保存失败')
  } finally {
    isSavingEmail.value = false
  }
}

async function savePassword() {
  if (!currentUser.value || isSavingPassword.value || !canSavePassword.value) return

  passwordErrorMessage.value = ''
  isSavingPassword.value = true
  try {
    const updated = await updateUser(currentUser.value.id, {
      password: newPassword.value,
      current_password: currentPassword.value.trim()
    })
    currentUser.value = updated
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    snackbar({ message: '密码已更新' })
  } catch (error: unknown) {
    passwordErrorMessage.value = extractErrorMessage(error, '保存失败')
  } finally {
    isSavingPassword.value = false
  }
}
</script>

<style scoped>
.profile-hero {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 22px;
  border-radius: 26px;
  background: linear-gradient(135deg, rgb(var(--mdui-color-surface-container-low)) 0%, rgb(var(--mdui-color-surface-container-high)) 100%);
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.6);
}

.profile-avatar {
  width: 72px;
  height: 72px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  font-size: 1.8rem;
  font-weight: 700;
  color: rgb(var(--mdui-color-on-primary));
  background: rgb(var(--mdui-color-primary));
  flex-shrink: 0;
}

.profile-summary {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.profile-field-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.profile-field-row--email {
  align-items: center;
}

.profile-name {
  min-width: 0;
  font-size: clamp(1.35rem, 2vw, 1.8rem);
  font-weight: 700;
  line-height: 1.15;
}

.profile-email {
  min-width: 0;
  flex: 0 1 auto;
  font-size: 0.98rem;
  word-break: break-all;
}

.profile-stat-value {
  margin-top: 10px;
  font-size: 1rem;
  line-height: 1.5;
}

.profile-stat-value--mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.edit-form,
.dialog-form {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.password-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-footer,
.dialog-actions {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.dialog-actions {
  flex-wrap: nowrap;
  align-items: center;
}

.error-message {
  font-size: 0.9rem;
  line-height: 1.5;
  color: rgb(var(--mdui-color-error));
}

@media (max-width: 960px) {
  .profile-hero,
  .password-grid,
  .form-footer {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }

  .dialog-actions {
    justify-content: flex-end;
  }

  .profile-hero {
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .profile-hero {
    padding: 18px;
    border-radius: 22px;
  }

  .profile-avatar {
    width: 60px;
    height: 60px;
    border-radius: 20px;
    font-size: 1.45rem;
  }
}
</style>
