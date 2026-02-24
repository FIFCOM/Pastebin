<template>
  <UserPanelCard title="两步验证（TOTP）" subtitle="使用验证器应用增强账户安全">
    <template #actions>
      <mdui-button
        variant="tonal"
        :disabled="!currentUser || isLoading"
        :loading="isLoading"
        @click="refresh"
      >
        刷新
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录</div>

    <div v-else class="content">
      <div class="status-row">
        <div class="status-label">当前状态</div>
        <mdui-chip :variant="status?.enabled ? 'filled' : 'outlined'">
          {{ status?.enabled ? '已启用' : '未启用' }}
        </mdui-chip>
      </div>

      <div class="hint">
        {{
          status?.enabled
            ? '如更换手机或丢失验证器，请立即联系管理员重置两步验证。'
            : '点击“生成二维码”后，使用验证器应用扫描二维码，并输入 6 位验证码完成验证。'
        }}
      </div>

      <div class="backup-note">
        重要提示：请保存验证器应用的迁移备份，避免设备丢失后无法登录。
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
          <div class="qr-box">
            <QrCode :value="setupInfo.provisioning_uri" :size="220" />
          </div>
        </div>

        <div class="secret-row">
          <div class="secret-label">密钥</div>
          <code class="secret">{{ setupInfo.secret }}</code>
          <mdui-button variant="tonal" @click="copySecret">复制</mdui-button>
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
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { confirm } from 'mdui/functions/confirm.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/chip.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import { disableTotp, getTotpStatus, setupTotp, verifyTotp } from '../../services/user'
import type { TotpSetupResponse, TotpStatusResponse } from '../../services/user'
import { extractErrorMessage } from '../../utils/error'
import QrCode from '../common/QrCode.vue'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

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
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取状态失败'), closeable: true })
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
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '生成失败'), closeable: true })
  } finally {
    isSettingUp.value = false
  }
}

async function copySecret() {
  if (!setupInfo.value) return

  try {
    await navigator.clipboard.writeText(setupInfo.value.secret)
    snackbar({ message: '密钥已复制' })
  } catch (error: unknown) {
    console.warn('Copy secret failed', error)
    snackbar({ message: '复制失败，请手动复制', closeable: true })
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
    setupInfo.value = null
    totpCode.value = ''
    await refresh()
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '验证失败'), closeable: true })
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
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '禁用失败'), closeable: true })
  } finally {
    isDisabling.value = false
  }
}

onMounted(() => {
  void refresh()
})
</script>

<style scoped>
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
}

.hint,
.backup-note {
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.setup-area {
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid rgb(var(--mdui-color-outline-variant));
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

.qr-box {
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
  font-size: 15px;
}

.secret {
  word-break: break-all;
  font-size: 15px;
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
