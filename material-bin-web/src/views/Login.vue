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

        <div class="auth-footer">
          还没有账号？
          <a href="" @click.prevent="goRegister">立即注册</a>
        </div>
      </mdui-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'

import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const { login } = useAuth()

const email = ref('')
const password = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

const canSubmit = computed(() => {
  return email.value.trim().length > 0 && password.value.length > 0
})

async function handleSubmit() {
  if (!canSubmit.value || isSubmitting.value) {
    return
  }
 
  isSubmitting.value = true
  errorMessage.value = ''
 
  try {
    await login(email.value.trim(), password.value)
    snackbar({ message: '登录成功' })
 
    const redirect = (route.query.redirect as string | undefined) || '/'
    await router.replace(redirect)
  } catch (e: any) {
    let msg = '登录失败，请检查邮箱或密码'
    if (e?.response?.data?.detail) {
      // 后端显式返回的业务错误信息
      msg = e.response.data.detail
    } else if (e?.response?.status === 401) {
      // 未授权统一视为邮箱或密码错误
      msg = '邮箱或密码错误'
    } else if (e instanceof Error) {
      // 其它网络错误等情况
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
</script>

<style scoped>
.auth-page {
  min-height: calc(100vh - 64px);
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
  color: var(--mdui-color-on-surface-variant);
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
  color: var(--mdui-color-error);
}

.auth-footer {
  margin-top: 16px;
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.auth-footer a {
  color: var(--mdui-color-primary);
  text-decoration: none;
  font-weight: 500;
}

.auth-footer a:hover {
  text-decoration: underline;
}
</style>