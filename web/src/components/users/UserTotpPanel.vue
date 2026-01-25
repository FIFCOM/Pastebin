<template>
  <mdui-card class="panel-card">
    <div class="panel-header">
      <div>
        <div class="panel-title">两步验证（TOTP）</div>
        <div class="panel-subtitle">增强登录安全性（如 Google Authenticator）</div>
      </div>
      <mdui-button
        variant="tonal"
        :disabled="!currentUser || isLoading"
        :loading="isLoading"
        @click="refresh"
      >
        刷新
      </mdui-button>
    </div>

    <mdui-divider></mdui-divider>

    <div v-if="!currentUser" class="empty-hint">请先登录</div>

    <div v-else class="content">
      <div class="status-row">
        <div class="status-label">当前状态</div>
        <mdui-chip :variant="status?.enabled ? 'filled' : 'outlined'">
          {{ status?.enabled ? '已启用' : '未启用' }}
        </mdui-chip>
      </div>

      <div v-if="!status?.enabled" class="hint">
        点击“生成二维码”后，使用验证器应用扫描二维码，并输入 6 位验证码完成验证。
      </div>

      <div class="actions">
        <mdui-button
          v-if="!status?.enabled"
          variant="filled"
          :disabled="isSettingUp"
          :loading="isSettingUp"
          @click="setup"
        >
          生成二维码
        </mdui-button>

        <mdui-button
          v-else
          variant="tonal"
          :disabled="isSettingUp"
          :loading="isSettingUp"
          @click="setup"
        >
          重新生成
        </mdui-button>

        <mdui-button
          v-if="status?.enabled"
          variant="text"
          :disabled="isDisabling"
          :loading="isDisabling"
          @click="disable"
        >
          禁用
        </mdui-button>
      </div>

      <div v-if="setupInfo" class="setup-area">
        <div class="setup-title">扫码绑定</div>

        <div class="qr-wrap">
          <img :src="setupInfo.qr_code_url" alt="TOTP QR Code" class="qr" />
        </div>

        <div class="secret-row">
          <div class="secret-label">密钥</div>
          <code class="secret">{{ setupInfo.secret }}</code>
        </div>

        <div class="verify-row">
          <mdui-text-field
            v-model="totpCode"
            label="验证码"
            placeholder="6 位数字"
            variant="outlined"
            type="text"
            maxlength="6"
            :disabled="isVerifying"
          ></mdui-text-field>

          <mdui-button
            variant="filled"
            :disabled="!canVerify || isVerifying"
            :loading="isVerifying"
            @click="verify"
          >
            验证
          </mdui-button>
        </div>
      </div>
    </div>
  </mdui-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import { confirm } from 'mdui/functions/confirm.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'
import 'mdui/components/chip.js'
import 'mdui/components/divider.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { disableTotp, getTotpStatus, setupTotp, verifyTotp } from '../../services/user'
import type { TotpSetupResponse, TotpStatusResponse } from '../../services/user'

const { currentUser } = useAuth()

const status = ref<TotpStatusResponse | null>(null)
const setupInfo = ref<TotpSetupResponse | null>(null)
const totpCode = ref('')

const isLoading = ref(false)
const isSettingUp = ref(false)
const isVerifying = ref(false)
const isDisabling = ref(false)

const canVerify = computed(() => /^\d{6}$/.test(totpCode.value.trim()))

async function refresh() {
  if (!currentUser.value) return
  isLoading.value = true
  try {
    status.value = await getTotpStatus()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '获取状态失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isLoading.value = false
  }
}

async function setup() {
  if (!currentUser.value) return
  isSettingUp.value = true
  try {
    setupInfo.value = await setupTotp()
    totpCode.value = ''
    await refresh()
    snackbar({ message: '已生成二维码，请扫码后输入验证码验证' })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '生成失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isSettingUp.value = false
  }
}

async function verify() {
  if (!currentUser.value) return
  if (!canVerify.value) {
    snackbar({ message: '请输入 6 位数字验证码', closeable: true })
    return
  }

  isVerifying.value = true
  try {
    const resp = await verifyTotp(totpCode.value.trim())
    snackbar({ message: resp.message })
    await refresh()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '验证失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isVerifying.value = false
  }
}

async function disable() {
  if (!currentUser.value) return

  try {
    await confirm({
      headline: '禁用两步验证',
      description: '确认禁用 TOTP 两步验证？禁用后登录将仅需邮箱与密码。',
      confirmText: '禁用',
      cancelText: '取消',
      closeOnEsc: true,
      closeOnOverlayClick: true
    })
  } catch {
    return
  }

  isDisabling.value = true
  try {
    const resp = await disableTotp()
    setupInfo.value = null
    totpCode.value = ''
    snackbar({ message: resp.message })
    await refresh()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '禁用失败'
    snackbar({ message: msg, closeable: true })
  } finally {
    isDisabling.value = false
  }
}

onMounted(() => {
  refresh()
})
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
  color: var(--mdui-color-on-surface-variant);
}

.empty-hint {
  margin: 16px 0 0;
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.content {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-label {
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.hint {
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.setup-area {
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid var(--mdui-color-outline-variant);
}

.setup-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.qr-wrap {
  display: flex;
  justify-content: center;
  padding: 12px;
}

.qr {
  width: 220px;
  height: 220px;
  background: #fff;
  border-radius: 12px;
  padding: 12px;
  box-sizing: border-box;
}

.secret-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.secret-label {
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.secret {
  word-break: break-all;
  font-size: 13px;
}

.verify-row {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: end;
}

@media (max-width: 640px) {
  .verify-row {
    grid-template-columns: 1fr;
  }
}
</style>
