<template>
  <div class="auth-page">
    <div class="auth-card-wrapper">
      <mdui-card v-if="!isResetMode && requireTotp" class="auth-card totp-card">
        <h1 class="auth-title">两步验证</h1>
        <p class="auth-subtitle">输入身份验证器中的 6 位验证码。</p>

        <form class="auth-form totp-form" @submit.prevent="handleSubmit">
          <CodeSlotsInput
            ref="totpInputRef"
            v-model="totpCode"
            class="totp-inputs"
            :length="TOTP_LENGTH"
            size="compact"
            label-prefix="验证码"
            aria-label="两步验证码输入框"
            inputmode="numeric"
            autocomplete="one-time-code"
            pattern="[0-9]*"
            paste-mode="replace"
            :disabled="isSubmitting"
            :normalizer="normalizeTotpCode"
            @complete="handleTotpComplete"
            @enter="handleSubmit"
          />

          <div v-if="errorMessage" class="error-message">
            {{ errorMessage }}
          </div>

          <mdui-button
            class="submit-button verifying-button"
            type="submit"
            variant="filled"
            :disabled="!canSubmit || isSubmitting"
          >
            <mdui-circular-progress
              v-if="isSubmitting"
              class="button-spinner"
            ></mdui-circular-progress>
            <span>{{ isSubmitting ? '正在验证' : '验证并登录' }}</span>
          </mdui-button>
        </form>

        <div class="auth-footer">
          <a href="" @click.prevent="clearTotpChallenge">返回登录</a>
        </div>
      </mdui-card>

      <mdui-card v-else class="auth-card">
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
            登录
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

          <div v-if="resetPasswordStrengthHint" class="password-hint">
            {{ resetPasswordStrengthHint }}
          </div>

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
            <span class="auth-footer-primary">
              还没有账号？
              <a href="" @click.prevent="goRegister">立即注册</a>
            </span>
            <template v-if="emailVerificationEnabled">
              <a class="auth-footer-secondary" href="" @click.prevent="openResetMode">忘记密码</a>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'
import 'mdui/components/checkbox.js'
import 'mdui/components/circular-progress.js'

import { useAuth } from '../composables/useAuth'
import { registerHeaderActions, unregisterHeaderActions } from '../composables/useHeaderActions'
import { resetPassword, sendEmailVerificationCode } from '../services/auth'
import { getPublicConfig } from '../services/config'
import CodeSlotsInput from '../components/common/CodeSlotsInput.vue'

const route = useRoute()
const router = useRouter()
const { login, loginWithTotp } = useAuth()
const HEADER_OWNER_ID = 'login-page'
const TOTP_LENGTH = 6
type CodeSlotsInputExpose = InstanceType<typeof CodeSlotsInput>

const email = ref('')
const password = ref('')
const totpCode = ref('')
const totpInputRef = ref<CodeSlotsInputExpose | null>(null)
const pendingTotpEmail = ref('')
const pendingTotpPassword = ref('')
const requireTotp = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const emailVerificationEnabled = ref(false)
const emailVerificationResendIntervalSeconds = ref(60)

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
let lastAutoSubmittedTotpCode = ''

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

const resetPasswordStrengthHint = computed(() => weakPasswordHint(resetNewPassword.value))

watch(email, () => {
  if (requireTotp.value) {
    if (isCurrentTotpCredential()) return
    clearTotpChallenge()
  }
  errorMessage.value = ''
})

watch(password, () => {
  if (requireTotp.value) {
    if (isCurrentTotpCredential()) return
    clearTotpChallenge()
  }
  errorMessage.value = ''
})

function isCurrentTotpCredential(): boolean {
  return email.value.trim() === pendingTotpEmail.value && password.value === pendingTotpPassword.value
}

function clearTotpChallenge(): void {
  requireTotp.value = false
  pendingTotpEmail.value = ''
  pendingTotpPassword.value = ''
  errorMessage.value = ''
  resetTotpDigits()
}

function normalizeTotpCode(raw: string): string {
  return raw.replace(/\D/g, '').slice(0, TOTP_LENGTH)
}

function focusTotpInput(index: number): void {
  totpInputRef.value?.focus(index)
}

function resetTotpDigits(): void {
  totpCode.value = ''
  lastAutoSubmittedTotpCode = ''
}

function handleTotpComplete(code: string): void {
  const normalized = normalizeTotpCode(code)
  if (normalized.length !== TOTP_LENGTH) return
  if (isSubmitting.value || lastAutoSubmittedTotpCode === normalized) return

  lastAutoSubmittedTotpCode = normalized
  void handleSubmit()
}

async function loadEmailVerificationConfig() {
  try {
    const config = await getPublicConfig()
    emailVerificationEnabled.value = config.email_verification_enabled
    emailVerificationResendIntervalSeconds.value = config.email_verification_resend_interval_seconds
  } catch {
    emailVerificationEnabled.value = false
    emailVerificationResendIntervalSeconds.value = 60
  }
}

function startResetCountdown() {
  resetResendSeconds.value = emailVerificationResendIntervalSeconds.value
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

function weakPasswordHint(value: string): string {
  if (!value) return ''
  const hasLetter = /[A-Za-z]/.test(value)
  const hasDigit = /\d/.test(value)
  const hasSymbol = /[^A-Za-z0-9]/.test(value)
  const variety = [hasLetter, hasDigit, hasSymbol].filter(Boolean).length
  if (value.length < 8) return '当前密码偏短，建议至少 8 位。'
  if (variety < 2) return '当前密码较容易被猜到，建议混合字母、数字或符号。'
  return ''
}

async function sendResetCode() {
  if (!canSendResetCode.value || isSendingResetCode.value || resetResendSeconds.value > 0) return

  isSendingResetCode.value = true
  resetErrorMessage.value = ''
  try {
    await sendEmailVerificationCode(resetEmail.value.trim(), 'reset_password')
    startResetCountdown()
    snackbar({ message: '如邮箱可用，验证码已发送', closeable: true })
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

  const submittedEmail = email.value.trim()
  const submittedPassword = password.value
  isSubmitting.value = true
  errorMessage.value = ''
  if (!requireTotp.value) {
    lastAutoSubmittedTotpCode = ''
  }

  try {
    if (requireTotp.value) {
      await loginWithTotp(submittedEmail, submittedPassword, totpCode.value.trim())
    } else {
      await login(submittedEmail, submittedPassword)
    }
    snackbar({ message: '登录成功' })

    const redirect = (route.query.redirect as string | undefined) || '/'
    await router.replace(redirect)
  } catch (e: any) {
    const detail = e?.response?.data?.detail

    if (!requireTotp.value && typeof detail === 'string' && detail.includes('两步验证')) {
      pendingTotpEmail.value = submittedEmail
      pendingTotpPassword.value = submittedPassword
      requireTotp.value = true
      resetTotpDigits()
      errorMessage.value = ''
      void nextTick(() => focusTotpInput(0))
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
    lastAutoSubmittedTotpCode = ''
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

.totp-card {
  text-align: center;
}

.totp-card .auth-title,
.totp-card .auth-subtitle {
  text-align: center;
}

.totp-form {
  align-items: stretch;
  gap: 18px;
}

.totp-inputs {
  margin: 6px 0 2px;
}

.verifying-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.button-spinner {
  width: 18px;
  height: 18px;
  color: currentColor;
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

.password-hint {
  margin-top: -8px;
  font-size: 13px;
  line-height: 1.45;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.error-message {
  font-size: 13px;
  color: rgb(var(--mdui-color-error));
}

.auth-footer {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  font-size: 13px;
}

.auth-footer-primary {
  min-width: 0;
}

.auth-footer-secondary {
  flex: 0 0 auto;
}

.auth-footer a {
  color: rgb(var(--mdui-color-primary));
  text-decoration: none;
  font-weight: 500;
}

.auth-footer a:hover {
  text-decoration: underline;
}

@media (max-width: 520px) {
  .verification-row {
    grid-template-columns: 1fr;
  }

  .auth-footer {
    align-items: flex-start;
  }
}
</style>
