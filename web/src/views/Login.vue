<template>
  <div class="auth-page">
    <div class="auth-card-wrapper">
      <mdui-card class="auth-card">
        <h1 class="auth-title">{{ isResetMode ? '重置密码' : '登录' }}</h1>
        <p class="auth-subtitle">{{ isResetMode ? '通过邮箱验证码设置新密码' : '使用邮箱和密码登录 Material Bin' }}</p>

        <form v-if="!isResetMode" class="auth-form" @submit.prevent="handleSubmit">
          <mdui-text-field
            v-model="email"
            label="邮箱"
            placeholder="请输入邮箱"
            variant="outlined"
            type="text"
            clearable
            :disabled="isSubmitting"
          ></mdui-text-field>

          <mdui-text-field
            v-model="password"
            label="密码"
            placeholder="请输入密码"
            type="password"
            variant="outlined"
            :disabled="isSubmitting"
            @keydown.enter="handleSubmit"
          ></mdui-text-field>

          <mdui-text-field
            v-if="requireTotp"
            v-model="totpCode"
            label="验证码"
            placeholder="6 位数字"
            type="text"
            variant="outlined"
            maxlength="6"
            :disabled="isSubmitting"
            @keydown.enter="handleSubmit"
          ></mdui-text-field>

          <div v-if="errorMessage" class="error-message">
            {{ errorMessage }}
          </div>

          <mdui-button
            class="submit-button"
            type="submit"
            variant="filled"
            :disabled="!canSubmit || isSubmitting"
            :loading="isSubmitting"
          >
            {{ requireTotp ? '验证并登录' : '登录' }}
          </mdui-button>
        </form>

        <form v-else class="auth-form" @submit.prevent="handlePasswordReset">
          <mdui-text-field
            v-model="resetEmail"
            label="邮箱"
            placeholder="请输入邮箱"
            variant="outlined"
            type="email"
            clearable
            :disabled="isResetSubmitting"
          ></mdui-text-field>

          <div class="verification-row">
            <mdui-text-field
              v-model="resetCode"
              label="邮箱验证码"
              placeholder="6 位数字"
              type="text"
              variant="outlined"
              maxlength="6"
              :disabled="isResetSubmitting"
            ></mdui-text-field>
            <mdui-button
              class="verification-button"
              type="button"
              variant="tonal"
              :disabled="!canSendResetCode || isSendingResetCode || resetResendSeconds > 0"
              :loading="isSendingResetCode"
              @click="sendResetCode"
            >
              {{ resetResendSeconds > 0 ? `${resetResendSeconds}s` : '发送验证码' }}
            </mdui-button>
          </div>

          <mdui-text-field
            v-model="resetNewPassword"
            label="新密码"
            placeholder="请输入新密码"
            type="password"
            variant="outlined"
            :disabled="isResetSubmitting"
          ></mdui-text-field>

          <mdui-text-field
            v-model="resetConfirmPassword"
            label="确认新密码"
            placeholder="请再次输入新密码"
            type="password"
            variant="outlined"
            :disabled="isResetSubmitting"
            @keydown.enter="handlePasswordReset"
          ></mdui-text-field>

          <div class="reset-warning">
            找回密码无法恢复旧账户密钥。重置后会清空当前账户保存的历史记录和收藏关联，Paste 本体不会删除。
          </div>

          <mdui-checkbox
            :checked="resetDataLossConfirmed"
            :disabled="isResetSubmitting"
            @change="handleResetConfirmChange"
          >
            我已了解并继续重置
          </mdui-checkbox>

          <div v-if="resetErrorMessage" class="error-message">
            {{ resetErrorMessage }}
          </div>

          <mdui-button
            class="submit-button"
            type="submit"
            variant="filled"
            :disabled="!canResetPassword || isResetSubmitting"
            :loading="isResetSubmitting"
          >
            重置密码
          </mdui-button>
        </form>

        <div class="auth-footer">
          <template v-if="!isResetMode">
            还没有账号？
            <a href="" @click.prevent="goRegister">立即注册</a>
            <template v-if="emailVerificationEnabled">
              <span class="footer-separator">·</span>
              <a href="" @click.prevent="openResetMode">忘记密码</a>
            </template>
          </template>
          <template v-else>
            想起密码？
            <a href="" @click.prevent="closeResetMode">返回登录</a>
          </template>
        </div>
      </mdui-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'
import 'mdui/components/checkbox.js'

import { useAuth } from '../composables/useAuth'
import { registerHeaderActions, unregisterHeaderActions } from '../composables/useHeaderActions'
import { resetPassword, sendEmailVerificationCode } from '../services/auth'
import { getPublicConfig } from '../services/config'

const route = useRoute()
const router = useRouter()
const { login, loginWithTotp } = useAuth()
const HEADER_OWNER_ID = 'login-page'

const email = ref('')
const password = ref('')
const totpCode = ref('')
const requireTotp = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const emailVerificationEnabled = ref(false)

const isResetMode = ref(false)
const resetEmail = ref('')
const resetCode = ref('')
const resetNewPassword = ref('')
const resetConfirmPassword = ref('')
const resetDataLossConfirmed = ref(false)
const isResetSubmitting = ref(false)
const isSendingResetCode = ref(false)
const resetErrorMessage = ref('')
const resetResendSeconds = ref(0)
let resetTimer: number | undefined

const canSubmit = computed(() => {
  if (email.value.trim().length === 0) return false
  if (password.value.length === 0) return false
  if (requireTotp.value) {
    return /^\d{6}$/.test(totpCode.value.trim())
  }
  return true
})

const canSendResetCode = computed(() => {
  return resetEmail.value.trim().length > 0 && !isResetSubmitting.value
})

const canResetPassword = computed(() => {
  return (
    resetEmail.value.trim().length > 0 &&
    /^\d{6}$/.test(resetCode.value.trim()) &&
    resetNewPassword.value.length > 0 &&
    resetNewPassword.value === resetConfirmPassword.value &&
    resetDataLossConfirmed.value
  )
})

watch(email, () => {
  requireTotp.value = false
  totpCode.value = ''
  errorMessage.value = ''
})

async function loadEmailVerificationConfig() {
  try {
    const config = await getPublicConfig()
    emailVerificationEnabled.value = config.email_verification_enabled
  } catch {
    emailVerificationEnabled.value = false
  }
}

function startResetCountdown() {
  resetResendSeconds.value = 60
  if (resetTimer !== undefined) window.clearInterval(resetTimer)
  resetTimer = window.setInterval(() => {
    resetResendSeconds.value = Math.max(0, resetResendSeconds.value - 1)
    if (resetResendSeconds.value === 0 && resetTimer !== undefined) {
      window.clearInterval(resetTimer)
      resetTimer = undefined
    }
  }, 1000)
}

function openResetMode() {
  resetEmail.value = email.value.trim()
  resetCode.value = ''
  resetNewPassword.value = ''
  resetConfirmPassword.value = ''
  resetDataLossConfirmed.value = false
  resetErrorMessage.value = ''
  isResetMode.value = true
}

function closeResetMode() {
  isResetMode.value = false
  resetErrorMessage.value = ''
  resetDataLossConfirmed.value = false
}

function handleResetConfirmChange(event: Event) {
  const target = event.target as { checked?: boolean } | null
  resetDataLossConfirmed.value = Boolean(target?.checked)
}

async function sendResetCode() {
  if (!canSendResetCode.value || isSendingResetCode.value || resetResendSeconds.value > 0) return

  isSendingResetCode.value = true
  resetErrorMessage.value = ''
  try {
    await sendEmailVerificationCode(resetEmail.value.trim(), 'reset_password')
    startResetCountdown()
    snackbar({ message: '验证码已发送，请检查邮箱', closeable: true })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || (e instanceof Error ? e.message : '发送验证码失败')
    resetErrorMessage.value = msg
    snackbar({ message: msg, closeable: true })
  } finally {
    isSendingResetCode.value = false
  }
}

async function handlePasswordReset() {
  if (!canResetPassword.value || isResetSubmitting.value) return

  isResetSubmitting.value = true
  resetErrorMessage.value = ''
  try {
    await resetPassword(resetEmail.value.trim(), resetNewPassword.value, resetCode.value.trim())
    snackbar({ message: '密码已重置，请使用新密码登录', closeable: true })
    email.value = resetEmail.value.trim()
    password.value = ''
    closeResetMode()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || (e instanceof Error ? e.message : '重置密码失败')
    resetErrorMessage.value = msg
    snackbar({ message: msg, closeable: true })
  } finally {
    isResetSubmitting.value = false
  }
}

async function handleSubmit() {
  if (!canSubmit.value || isSubmitting.value) {
    return
  }

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    if (requireTotp.value) {
      await loginWithTotp(email.value.trim(), password.value, totpCode.value.trim())
    } else {
      await login(email.value.trim(), password.value)
    }
    snackbar({ message: '登录成功' })

    const redirect = (route.query.redirect as string | undefined) || '/'
    await router.replace(redirect)
  } catch (e: any) {
    const detail = e?.response?.data?.detail

    if (!requireTotp.value && typeof detail === 'string' && detail.includes('两步验证')) {
      requireTotp.value = true
      totpCode.value = ''
      const msg = '此账户启用了两步验证，请输入 6 位验证码'
      errorMessage.value = msg
      snackbar({ message: msg, closeable: true })
      return
    }

    let msg = requireTotp.value ? '登录失败，请检查验证码' : '登录失败，请检查邮箱或密码'
    if (detail) {
      msg = detail
    } else if (e?.response?.status === 401) {
      msg = requireTotp.value ? '邮箱、密码或验证码错误' : '邮箱或密码错误'
    } else if (e instanceof Error) {
      msg = '登录失败：' + e.message
    }

    errorMessage.value = msg
    snackbar({ message: msg, closeable: true })
  } finally {
    isSubmitting.value = false
  }
}

function goRegister() {
  const redirect = (route.query.redirect as string | undefined) || '/'
  router.push({
    path: '/register',
    query: redirect ? { redirect } : undefined
  })
}

onMounted(() => {
  void loadEmailVerificationConfig()
  registerHeaderActions(HEADER_OWNER_ID, [
    {
      id: 'login-new-paste',
      label: '新建 Paste',
      ariaLabel: '新建 Paste',
      icon: 'add',
      kind: 'icon',
      onClick: () => { void router.push('/') }
    }
  ])
})

onBeforeUnmount(() => {
  if (resetTimer !== undefined) window.clearInterval(resetTimer)
  unregisterHeaderActions(HEADER_OWNER_ID)
})
</script>

<style scoped>
.auth-page {
  min-height: calc(100dvh - var(--app-header-offset, 64px) - 64px);
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 0;
}

.auth-card-wrapper {
  width: 100%;
  max-width: 420px;
  padding: 0 16px;
}

.auth-card {
  padding: 24px 24px 20px 24px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
}

.auth-title {
  margin: 0 0 4px 0;
  font-size: 24px;
  font-weight: 600;
}

.auth-subtitle {
  margin: 0 0 16px 0;
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 8px;
}

.submit-button {
  margin-top: 4px;
  width: 100%;
}

.verification-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: start;
}

.verification-button {
  min-width: 112px;
  margin-top: 4px;
}

.reset-warning {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgb(var(--mdui-color-error) / 0.35);
  background: rgb(var(--mdui-color-error-container) / 0.62);
  color: rgb(var(--mdui-color-on-error-container));
  font-size: 13px;
  line-height: 1.55;
}

.error-message {
  font-size: 13px;
  color: rgb(var(--mdui-color-error));
}

.auth-footer {
  margin-top: 16px;
  font-size: 13px;
}

.auth-footer a {
  color: rgb(var(--mdui-color-primary));
  text-decoration: none;
  font-weight: 500;
}

.auth-footer a:hover {
  text-decoration: underline;
}

.footer-separator {
  margin: 0 6px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

@media (max-width: 520px) {
  .verification-row {
    grid-template-columns: 1fr;
  }
}
</style>
