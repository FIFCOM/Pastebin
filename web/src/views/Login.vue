<template>
  <div class="auth-page">
    <div class="auth-card-wrapper">
      <mdui-card class="auth-card">
        <h1 class="auth-title">登录</h1>
        <p class="auth-subtitle">使用邮箱和密码登录 Material Bin</p>
 
        <form class="auth-form" @submit.prevent="handleSubmit">
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

        <div class="auth-footer">
          还没有账号？
          <a href="" @click.prevent="goRegister">立即注册</a>
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

import { useAuth } from '../composables/useAuth'
import { registerHeaderActions, unregisterHeaderActions } from '../composables/useHeaderActions'

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

const canSubmit = computed(() => {
  if (email.value.trim().length === 0) return false
  if (password.value.length === 0) return false
  if (requireTotp.value) {
    return /^\d{6}$/.test(totpCode.value.trim())
  }
  return true
})

watch(email, () => {
  // 账号切换时清理 TOTP 状态
  requireTotp.value = false
  totpCode.value = ''
  errorMessage.value = ''
})

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
</style>
