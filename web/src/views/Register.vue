<template>
  <div class="auth-page">
    <div class="auth-card-wrapper">
      <mdui-card class="auth-card">
        <h1 class="auth-title">注册</h1>
        <p class="auth-subtitle">创建一个新账户以使用 Material Bin</p>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <mdui-text-field
            v-model="email"
            label="邮箱"
            placeholder="name@example.com"
            type="email"
            variant="outlined"
            clearable
            :disabled="isSubmitting"
          ></mdui-text-field>

          <div v-if="emailVerificationEnabled" class="verification-row">
            <mdui-text-field
              v-model="verificationCode"
              label="邮箱验证码"
              placeholder="6 位数字"
              type="text"
              variant="outlined"
              maxlength="6"
              :disabled="isSubmitting"
            ></mdui-text-field>
            <mdui-button
              class="verification-button"
              type="button"
              variant="tonal"
              :disabled="!canSendCode || isSendingCode || resendSeconds > 0"
              :loading="isSendingCode"
              @click="sendRegisterCode"
            >
              {{ resendSeconds > 0 ? `${resendSeconds}s` : '发送验证码' }}
            </mdui-button>
          </div>

          <mdui-text-field
            v-model="password"
            label="密码"
            placeholder="请输入密码"
            type="password"
            variant="outlined"
            :disabled="isSubmitting"
          ></mdui-text-field>

          <mdui-text-field
            v-model="confirmPassword"
            label="确认密码"
            placeholder="请再次输入密码"
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
            注册并登录
          </mdui-button>
        </form>

        <div class="auth-footer">
          已有账号？
          <a href="" @click.prevent="goLogin">前往登录</a>
        </div>
      </mdui-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'

import { useAuth } from '../composables/useAuth'
import { registerHeaderActions, unregisterHeaderActions } from '../composables/useHeaderActions'
import { sendEmailVerificationCode } from '../services/auth'
import { getPublicConfig } from '../services/config'

const route = useRoute()
const router = useRouter()
const { registerAndAutoLogin } = useAuth()
const HEADER_OWNER_ID = 'register-page'

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const verificationCode = ref('')
const emailVerificationEnabled = ref(false)
const isSubmitting = ref(false)
const isSendingCode = ref(false)
const errorMessage = ref('')
const resendSeconds = ref(0)
let resendTimer: number | undefined

const canSubmit = computed(() => {
  return (
    email.value.trim().length > 0 &&
    password.value.length > 0 &&
    confirmPassword.value.length > 0 &&
    (!emailVerificationEnabled.value || /^\d{6}$/.test(verificationCode.value.trim()))
  )
})

const canSendCode = computed(() => {
  return email.value.trim().length > 0 && !isSubmitting.value
})

function startResendCountdown() {
  resendSeconds.value = 60
  if (resendTimer !== undefined) window.clearInterval(resendTimer)
  resendTimer = window.setInterval(() => {
    resendSeconds.value = Math.max(0, resendSeconds.value - 1)
    if (resendSeconds.value === 0 && resendTimer !== undefined) {
      window.clearInterval(resendTimer)
      resendTimer = undefined
    }
  }, 1000)
}

async function loadEmailVerificationConfig() {
  try {
    const config = await getPublicConfig()
    emailVerificationEnabled.value = config.email_verification_enabled
  } catch {
    emailVerificationEnabled.value = false
  }
}

async function sendRegisterCode() {
  if (!canSendCode.value || isSendingCode.value || resendSeconds.value > 0) return

  isSendingCode.value = true
  errorMessage.value = ''
  try {
    await sendEmailVerificationCode(email.value.trim(), 'register')
    startResendCountdown()
    snackbar({ message: '验证码已发送，请检查邮箱', closeable: true })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || (e instanceof Error ? e.message : '发送验证码失败')
    errorMessage.value = msg
    snackbar({ message: msg, closeable: true })
  } finally {
    isSendingCode.value = false
  }
}

function validateForm(): boolean {
  if (!email.value.trim()) {
    errorMessage.value = '邮箱不能为空'
    return false
  }
  if (!password.value) {
    errorMessage.value = '密码不能为空'
    return false
  }
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致'
    return false
  }
  if (password.value.length < 6) {
    // 后端只要求 SHA256 长度，这里做一个最基本的前端长度提示
    errorMessage.value = '建议密码长度不少于 6 位'
    // 仍然允许提交，只是提示
  }
  if (emailVerificationEnabled.value && !/^\d{6}$/.test(verificationCode.value.trim())) {
    errorMessage.value = '请输入6位邮箱验证码'
    return false
  }
  return true
}

async function handleSubmit() {
  if (!canSubmit.value || isSubmitting.value) {
    return
  }

  errorMessage.value = ''
  if (!validateForm()) {
    snackbar({ message: errorMessage.value, closeable: true })
    // 如果是长度建议类提示但 errorMessage 为空，则继续
    if (!errorMessage.value) {
      // do nothing
    } else {
      return
    }
  }

  isSubmitting.value = true

  try {
    await registerAndAutoLogin(
      email.value.trim(),
      password.value,
      emailVerificationEnabled.value ? verificationCode.value.trim() : undefined
    )
    snackbar({ message: '注册并登录成功' })

    const redirect = (route.query.redirect as string | undefined) || '/'
    await router.replace(redirect)
  } catch (e: any) {
    let msg = '注册失败，请检查邮箱是否有效或是否已被使用'
    if (e?.response?.data?.detail) {
      msg = e.response.data.detail
    } else if (e instanceof Error) {
      msg = e.message
    }
    errorMessage.value = msg
    snackbar({ message: msg, closeable: true })
  } finally {
    isSubmitting.value = false
  }
}

function goLogin() {
  const redirect = (route.query.redirect as string | undefined) || '/'
  router.push({
    path: '/login',
    query: redirect ? { redirect } : undefined
  })
}

onMounted(() => {
  void loadEmailVerificationConfig()
  registerHeaderActions(HEADER_OWNER_ID, [
    {
      id: 'register-new-paste',
      label: '新建 Paste',
      ariaLabel: '新建 Paste',
      icon: 'add',
      kind: 'icon',
      onClick: () => { void router.push('/') }
    }
  ])
})

onBeforeUnmount(() => {
  if (resendTimer !== undefined) window.clearInterval(resendTimer)
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
  /* 让卡片和 auth-card-wrapper 的内容区同宽，并在其中水平居中 */
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

@media (max-width: 520px) {
  .verification-row {
    grid-template-columns: 1fr;
  }
}
</style>
