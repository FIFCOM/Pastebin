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
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'

import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const { registerAndAutoLogin } = useAuth()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

const canSubmit = computed(() => {
  return (
    email.value.trim().length > 0 &&
    password.value.length > 0 &&
    confirmPassword.value.length > 0
  )
})

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
    await registerAndAutoLogin(email.value.trim(), password.value)
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