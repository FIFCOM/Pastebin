<template>
  <UserPanelCard title="我的账户">
    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>

    <div v-else class="user-panel-stack">
      <section class="profile-hero">
        <div class="profile-avatar" :aria-label="`用户 ${currentUser.username}`">{{ avatarText }}</div>

        <div class="profile-summary">
          <div class="profile-overline">账户信息</div>

          <div class="profile-field-row">
            <div class="profile-name">{{ currentUser.username }}</div>
            <mdui-button-icon
              icon="edit"
              aria-label="修改用户名"
              title="修改用户名"
              @click="openUsernameDialog"
            ></mdui-button-icon>
          </div>

          <div class="profile-field-row profile-field-row--email">
            <div class="profile-email">{{ currentUser.email ?? '未设置邮箱' }}</div>
            <mdui-button-icon
              icon="edit"
              aria-label="修改邮箱"
              title="修改邮箱"
              @click="openEmailDialog"
            ></mdui-button-icon>
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
          <div class="user-panel-section-heading">
            <div class="user-panel-section-eyebrow">安全</div>
            <div class="user-panel-section-title">修改密码</div>
            <div class="user-panel-section-copy">更新当前登录密码；保存后不会影响现有页面的数据流和账户信息展示。</div>
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

        <div v-if="emailVerificationEnabled" class="verification-row">
          <mdui-text-field
            v-model="emailVerificationCode"
            label="邮箱验证码"
            placeholder="6 位数字"
            type="text"
            variant="outlined"
            maxlength="6"
            :disabled="isSavingEmail"
          ></mdui-text-field>
          <mdui-button
            class="verification-button"
            variant="tonal"
            :disabled="!canSendEmailCode || isSendingEmailCode || emailResendSeconds > 0"
            :loading="isSendingEmailCode"
            @click="sendEmailCode"
          >
            {{ emailResendSeconds > 0 ? `${emailResendSeconds}s` : '发送验证码' }}
          </mdui-button>
        </div>

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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/dialog.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { getPublicConfig } from '../../services/config'
import { sendChangeEmailVerificationCode, updateUser } from '../../services/user'
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
const emailVerificationCode = ref('')
const emailVerificationEnabled = ref(false)
const emailErrorMessage = ref('')
const isSavingEmail = ref(false)
const isSendingEmailCode = ref(false)
const emailResendSeconds = ref(0)
let emailResendTimer: number | undefined

watch(
  currentUser,
  (user) => {
    usernameDraft.value = user?.username ?? ''
    emailDraft.value = user?.email ?? ''
    emailCurrentPassword.value = ''
    emailVerificationCode.value = ''
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
      emailCurrentPassword.value.trim() &&
      (!emailVerificationEnabled.value || /^\d{6}$/.test(emailVerificationCode.value.trim()))
  )
})

const canSendEmailCode = computed(() => {
  const email = emailDraft.value.trim()
  return Boolean(currentUser.value && email && email !== (currentUser.value.email ?? '') && !isSavingEmail.value)
})

async function loadEmailVerificationConfig() {
  try {
    const config = await getPublicConfig()
    emailVerificationEnabled.value = config.email_verification_enabled
  } catch {
    emailVerificationEnabled.value = false
  }
}

function startEmailResendCountdown() {
  emailResendSeconds.value = 60
  if (emailResendTimer !== undefined) window.clearInterval(emailResendTimer)
  emailResendTimer = window.setInterval(() => {
    emailResendSeconds.value = Math.max(0, emailResendSeconds.value - 1)
    if (emailResendSeconds.value === 0 && emailResendTimer !== undefined) {
      window.clearInterval(emailResendTimer)
      emailResendTimer = undefined
    }
  }, 1000)
}

async function sendEmailCode() {
  if (!canSendEmailCode.value || isSendingEmailCode.value || emailResendSeconds.value > 0) return

  isSendingEmailCode.value = true
  emailErrorMessage.value = ''
  try {
    await sendChangeEmailVerificationCode(emailDraft.value.trim())
    startEmailResendCountdown()
    snackbar({ message: '验证码已发送，请检查新邮箱', closeable: true })
  } catch (error: unknown) {
    const msg = extractErrorMessage(error, '发送验证码失败')
    emailErrorMessage.value = msg
    snackbar({ message: msg, closeable: true })
  } finally {
    isSendingEmailCode.value = false
  }
}

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
  emailVerificationCode.value = ''
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
  emailVerificationCode.value = ''
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
  if (!currentUser.value || isSavingEmail.value) return

  const nextEmail = emailDraft.value.trim()
  if (!nextEmail) {
    emailErrorMessage.value = '邮箱不能为空'
    return
  }

  if (!canSaveEmail.value) return

  isSavingEmail.value = true
  emailErrorMessage.value = ''
  try {
    const updated = await updateUser(currentUser.value.id, {
      email: nextEmail,
      current_password: emailCurrentPassword.value.trim(),
      email_verification_code: emailVerificationEnabled.value ? emailVerificationCode.value.trim() : undefined
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

onMounted(() => {
  void loadEmailVerificationConfig()
})

onBeforeUnmount(() => {
  if (emailResendTimer !== undefined) window.clearInterval(emailResendTimer)
})
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
  gap: 12px;
}

.profile-overline {
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgb(var(--mdui-color-on-surface-variant));
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

.verification-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
}

.verification-button {
  min-width: 112px;
  margin-top: 4px;
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
  .verification-row,
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
