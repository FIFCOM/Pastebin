<template>
  <UserPanelCard title="两步验证">
    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>

    <div v-else class="user-panel-stack">
      <section class="user-panel-section user-panel-section--soft totp-overview">
        <div class="totp-status-summary" :data-enabled="status?.enabled ? 'true' : 'false'">
          <span class="totp-status-icon">
            <mdui-icon :name="status?.enabled ? 'verified_user' : 'security'"></mdui-icon>
          </span>
          <div class="totp-status-text">
            <div class="totp-status-label">两步验证</div>
            <div class="totp-status-value">{{ status?.enabled ? '已启用' : '未启用' }}</div>
            <div class="totp-status-copy">
              {{ status?.enabled ? '登录需验证码' : '登录仅需密码' }}
            </div>
          </div>
        </div>

        <div class="totp-overview-main">
          <div class="user-panel-section-header">
            <div class="user-panel-section-heading">
              <div class="user-panel-section-eyebrow">设置</div>
              <div class="user-panel-section-title">验证器设置</div>
              <div class="user-panel-section-copy">
                使用
                <a class="setup-link" href="https://support.google.com/accounts/answer/1066447" target="_blank" rel="noreferrer">Google Authenticator</a>
                、
                <a class="setup-link" href="https://support.1password.com/one-time-passwords/" target="_blank" rel="noreferrer">1Password</a>
                等软件扫描二维码绑定；无法扫描时可手动复制密钥。
              </div>
            </div>
          </div>
        </div>

        <div class="totp-action-row">
          <mdui-button
            v-if="!status?.enabled"
            variant="filled"
            :disabled="isSettingUp"
            :loading="isSettingUp"
            @click="setup"
          >
            <mdui-icon slot="icon" name="qr_code"></mdui-icon>
            启用
          </mdui-button>
          <template v-else>
            <mdui-button
              variant="tonal"
              :disabled="isSettingUp"
              :loading="isSettingUp"
              @click="setup"
            >
              <mdui-icon slot="icon" name="autorenew"></mdui-icon>
              重新生成
            </mdui-button>
            <mdui-button
              variant="text"
              :disabled="isDisabling"
              :loading="isDisabling"
              @click="disable"
            >
              <mdui-icon slot="icon" name="block"></mdui-icon>
              禁用
            </mdui-button>
          </template>
        </div>
      </section>

      <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

      <section v-if="setupInfo" class="user-panel-section user-panel-section--soft setup-panel">
        <div class="user-panel-section-header">
          <div class="user-panel-section-heading">
            <div class="user-panel-section-eyebrow">绑定</div>
            <div class="user-panel-section-title">绑定验证器</div>
            <div class="user-panel-section-copy">扫码或复制设置密钥后，输入当前验证码完成绑定。</div>
          </div>
        </div>

        <div class="setup-grid">
          <div class="qr-card">
            <QrCode :value="setupInfo.provisioning_uri" :size="220" />
          </div>

          <div class="setup-form">
            <div>
              <div class="setup-label">设置密钥</div>
              <div class="setup-secret-row">
                <code class="user-panel-code">{{ setupInfo.secret }}</code>
                <mdui-button variant="tonal" @click="copySecret">复制</mdui-button>
              </div>
            </div>

            <mdui-text-field
              v-model="totpCode"
              label="验证码"
              placeholder="6 位数字"
              variant="outlined"
              type="text"
              maxlength="6"
              :disabled="isVerifying"
            ></mdui-text-field>

            <div class="setup-actions">
              <mdui-button
                variant="filled"
                :disabled="!canVerify || isVerifying"
                :loading="isVerifying"
                @click="verify"
              >
                验证并启用
              </mdui-button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { confirm } from 'mdui/functions/confirm.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
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
    snackbar({ message: '已生成二维码，请继续完成验证' })
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
    snackbar({ message: '设置密钥已复制' })
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
.totp-overview {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr) max-content;
  align-items: center;
  gap: 18px 24px;
}

.totp-status-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 178px;
  padding-right: 24px;
  border-right: 1px solid rgb(var(--mdui-color-outline-variant) / 0.7);
}

.totp-status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border-radius: 14px;
  color: rgb(var(--mdui-color-on-primary-container));
  background: rgb(var(--mdui-color-primary-container));
}

.totp-status-summary[data-enabled='false'] .totp-status-icon {
  color: rgb(var(--mdui-color-on-surface-variant));
  background: rgb(var(--mdui-color-surface-container-high));
}

.totp-status-text {
  min-width: 0;
}

.totp-status-label {
  font-size: 0.78rem;
  line-height: 1.2;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.totp-status-value {
  margin-top: 3px;
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.25;
  color: rgb(var(--mdui-color-on-surface));
}

.totp-status-copy {
  margin-top: 4px;
  font-size: 0.82rem;
  line-height: 1.3;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.totp-overview-main {
  min-width: 0;
}

.totp-action-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.setup-panel {
  overflow: hidden;
}

.setup-link {
  color: rgb(var(--mdui-color-primary));
  text-decoration: none;
}

.setup-link:hover {
  text-decoration: underline;
}

.setup-grid {
  display: grid;
  grid-template-columns: max-content minmax(320px, 1fr);
  gap: 16px;
  align-items: center;
}

.qr-card {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  padding: 20px;
  box-sizing: border-box;
  border-radius: 24px;
  background: #fff;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.7);
  justify-self: start;
}

.setup-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  justify-content: center;
  min-width: 0;
}

.setup-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.setup-secret-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.setup-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 960px) {
  .totp-overview {
    grid-template-columns: 1fr;
  }

  .totp-status-summary {
    min-width: 0;
    padding-right: 0;
    padding-bottom: 14px;
    border-right: 0;
    border-bottom: 1px solid rgb(var(--mdui-color-outline-variant) / 0.7);
  }

  .totp-action-row {
    justify-content: flex-start;
  }

  .setup-grid {
    grid-template-columns: 1fr;
  }

  .qr-card {
    width: fit-content;
    justify-self: center;
    padding: 16px;
  }

  .setup-actions {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 640px) {
  .totp-action-row {
    flex-direction: column;
    align-items: stretch;
  }

  .qr-card {
    width: fit-content;
    padding: 12px;
    border-radius: 20px;
  }

  .setup-secret-row {
    align-items: stretch;
  }
}
</style>
