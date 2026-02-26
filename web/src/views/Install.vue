<template>
  <div class="install-page">
    <div class="install-card-wrapper">
      <mdui-card v-if="showRestartCard" class="install-card restart-card">
        <h1 class="install-title">安装已完成</h1>
        <p class="install-subtitle">已生成 .env，新配置会在服务端重启后自动生效。</p>
        <div class="restart-banner">
          <div class="restart-banner-title">正在等待服务端重启</div>
          <div v-if="isRestartPolling" class="restart-loading-row">
            <mdui-circular-progress></mdui-circular-progress>
            <div class="restart-loading-text">正在自动检测重启状态，恢复后将继续安装流程。</div>
          </div>
          <div v-if="effectiveRestartMessage" class="restart-banner-detail">{{ effectiveRestartMessage }}</div>
          <div v-if="restartPollTimedOut" class="restart-timeout-hint">
            自动检测超过 1 分钟仍未完成，请手动重启服务端。
          </div>
          <div v-else-if="showManualRestartHint" class="restart-banner-detail">
            如果长时间未重启，则请尝试手动重启。
          </div>
        </div>
        <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>
        <mdui-button
          v-if="restartPollTimedOut"
          class="submit-button"
          variant="filled"
          :disabled="isLoading"
          @click="handleRestartCheck"
        >
          手动重启后重新检测
        </mdui-button>
      </mdui-card>

      <mdui-card v-else class="install-card">
        <h1 class="install-title">系统安装向导</h1>

        <mdui-linear-progress v-if="isLoading"></mdui-linear-progress>

        <div v-if="status" class="steps" aria-label="安装进度">
          <div
            class="step-connector step-connector-head"
            :class="{ done: stepStates.env !== 'pending' }"
            aria-hidden="true"
          ></div>

          <div class="step-node step-node-start" :class="`is-${stepStates.env}`">
            <div class="step-circle">{{ stepStates.env === 'done' ? '✓' : '1' }}</div>
          </div>

          <div
            class="step-connector step-connector-mid"
            :class="{ done: stepStates.env === 'done' }"
            aria-hidden="true"
          ></div>

          <div class="step-node step-node-end" :class="`is-${stepStates.admin}`">
            <div class="step-circle">{{ stepStates.admin === 'done' ? '✓' : '2' }}</div>
          </div>

          <div
            class="step-connector step-connector-tail"
            :class="{ done: stepStates.admin === 'done' }"
            aria-hidden="true"
          ></div>

          <div class="step-content step-content-start">
            <div class="step-title">配置环境变量</div>
            <div class="step-subtitle">{{ stepStateLabel(stepStates.env) }}</div>
          </div>

          <div class="step-content step-content-end">
            <div class="step-title">创建系统管理员</div>
            <div class="step-subtitle">{{ stepStateLabel(stepStates.admin) }}</div>
          </div>
        </div>

        <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

        <form v-if="status" class="install-form" @submit.prevent="handleSubmit">
          <section v-if="isEnvStep" class="form-section">
            <div v-for="group in basicEnvGroups" :key="`basic-${group.name}`" class="env-group">
              <h3 class="group-title">{{ group.name }}</h3>
              <div class="env-grid">
                <div v-for="item in group.items" :key="item.key" class="env-item">
                  <div v-if="item.key === 'DATABASE_URL'" class="database-mode-row">
                    <div class="database-mode-label">数据库类型</div>
                    <mdui-segmented-button-group
                      :value="databaseMode"
                      selects="single"
                      required
                      :disabled="isSubmitting"
                      @change="handleDatabaseModeChange"
                    >
                      <mdui-segmented-button value="sqlite">SQLite</mdui-segmented-button>
                      <mdui-segmented-button value="mysql">MySQL</mdui-segmented-button>
                    </mdui-segmented-button-group>
                    <br>
                  </div>
                  <mdui-text-field
                    v-model="envValues[item.key]"
                    :label="item.required ? `${item.key} *` : item.key"
                    variant="outlined"
                    :placeholder="item.key === 'DATABASE_URL' ? databaseUrlPlaceholder : item.default_value"
                    :disabled="isSubmitting"
                  >
                    <mdui-button-icon
                      v-if="canGenerateSecret(item.key)"
                      slot="end-icon"
                      icon="refresh"
                      type="button"
                      class="random-secret-icon"
                      :disabled="isSubmitting"
                      @click.stop="handleGenerateSecret(item.key)"
                    ></mdui-button-icon>
                  </mdui-text-field>
                  <div v-if="item.comment && item.key !== 'DATABASE_URL'" class="env-comment">{{ item.comment }}</div>
                </div>
              </div>
            </div>

            <button
              v-if="advancedEnvGroups.length > 0"
              type="button"
              class="advanced-toggle"
              :class="{ open: showAdvanced }"
              :disabled="isSubmitting"
              :aria-expanded="showAdvanced ? 'true' : 'false'"
              @click="showAdvanced = !showAdvanced"
            >
              <span class="advanced-toggle-chevron" aria-hidden="true"></span>
              <span>高级配置</span>
            </button>

            <div v-show="showAdvanced" class="advanced-config">
              <div v-for="group in advancedEnvGroups" :key="`advanced-${group.name}`" class="env-group">
                <h3 class="group-title">{{ group.name }}</h3>
                <div class="env-grid">
                  <div v-for="item in group.items" :key="item.key" class="env-item">
                    <div v-if="item.key === 'DATABASE_URL'" class="database-mode-row">
                      <div class="database-mode-label">数据库类型</div>
                      <mdui-segmented-button-group
                        :value="databaseMode"
                        selects="single"
                        required
                        :disabled="isSubmitting"
                        @change="handleDatabaseModeChange"
                      >
                        <mdui-segmented-button value="sqlite">SQLite</mdui-segmented-button>
                        <mdui-segmented-button value="mysql">MySQL</mdui-segmented-button>
                      </mdui-segmented-button-group>
                    </div>
                    <mdui-text-field
                      v-model="envValues[item.key]"
                      :label="item.required ? `${item.key} *` : item.key"
                      variant="outlined"
                      :placeholder="item.key === 'DATABASE_URL' ? databaseUrlPlaceholder : item.default_value"
                      :disabled="isSubmitting"
                    >
                      <mdui-button-icon
                        v-if="canGenerateSecret(item.key)"
                        slot="end-icon"
                        icon="refresh"
                        type="button"
                        class="random-secret-icon"
                        :disabled="isSubmitting"
                        @click.stop="handleGenerateSecret(item.key)"
                      ></mdui-button-icon>
                    </mdui-text-field>
                    <div v-if="item.comment && item.key !== 'DATABASE_URL'" class="env-comment">{{ item.comment }}</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="missingRequiredEnvKeys.length > 0" class="required-hint">
              必填项未完成：{{ missingRequiredEnvKeys.join(', ') }}
            </div>
          </section>

          <section v-if="isAdminStep" class="form-section">
            <div class="step-hint">已完成基础配置，请创建首个管理员账户。</div>
            <mdui-text-field
              v-model="adminEmail"
              label="管理员邮箱 *"
              type="email"
              variant="outlined"
              :disabled="isSubmitting"
            ></mdui-text-field>

            <mdui-text-field
              v-model="adminPassword"
              label="管理员密码 *"
              type="password"
              variant="outlined"
              :disabled="isSubmitting"
            ></mdui-text-field>

            <mdui-text-field
              v-model="adminPasswordConfirm"
              label="确认管理员密码 *"
              type="password"
              variant="outlined"
              :disabled="isSubmitting"
            ></mdui-text-field>
            <div v-if="passwordMismatch" class="field-error">两次密码不一致</div>
          </section>

          <mdui-button
            class="submit-button"
            type="submit"
            variant="filled"
            :disabled="!canSubmit || isSubmitting"
            :loading="isSubmitting"
          >
            {{ submitButtonLabel }}
          </mdui-button>
        </form>
      </mdui-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/card.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/segmented-button-group.js'
import 'mdui/components/segmented-button.js'
import 'mdui/components/text-field.js'

import { sha256Hex } from '../services/auth'
import {
  fetchInstallContext,
  runInstallSetup,
  type InstallEnvItem,
  type InstallContextResponse
} from '../services/install'
import { extractErrorMessage } from '../utils/error'

const router = useRouter()

const status = ref<InstallContextResponse | null>(null)
const isLoading = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const restartRequired = ref(false)
const restartMessage = ref('')
const showManualRestartHint = ref(false)
const restartPollTimedOut = ref(false)

const RESTART_POLL_INTERVAL_MS = 1500
const RESTART_MANUAL_HINT_MS = 30000
const RESTART_POLL_TIMEOUT_MS = 60000
let restartPollTimer: number | null = null
let restartHintTimer: number | null = null
let restartTimeoutTimer: number | null = null
const isRestartPolling = ref(false)

const envValues = ref<Record<string, string>>({})
const SQLITE_DATABASE_URL = 'sqlite:///./material_bin.db'
const MYSQL_DATABASE_URL = 'mysql+pymysql://username:password@localhost:3306/material_bin'
const RANDOM_SECRET_KEYS = new Set(['SECRET_KEY', 'MEMBER_TOKEN_SECRET_KEY', 'INTERNAL_TOKEN'])

const adminEmail = ref('')
const adminPassword = ref('')
const adminPasswordConfirm = ref('')
const showAdvanced = ref(false)

type EnvGroup = { name: string; items: InstallEnvItem[] }

function buildEnvGroups(items: InstallEnvItem[], advanced: boolean): EnvGroup[] {
  const groups = new Map<string, InstallEnvItem[]>()
  for (const item of items) {
    if (item.advanced !== advanced) continue

    const name = item.group?.trim() || '其它配置'
    const existing = groups.get(name)
    if (existing) {
      existing.push(item)
    } else {
      groups.set(name, [item])
    }
  }

  return Array.from(groups.entries()).map(([name, groupedItems]) => ({ name, items: groupedItems }))
}

const basicEnvGroups = computed<EnvGroup[]>(() => {
  const currentStatus = status.value
  if (!currentStatus || currentStatus.env_exists) return []
  return buildEnvGroups(currentStatus.env_template, false)
})

const advancedEnvGroups = computed<EnvGroup[]>(() => {
  const currentStatus = status.value
  if (!currentStatus || currentStatus.env_exists) return []
  return buildEnvGroups(currentStatus.env_template, true)
})

const missingRequiredEnvKeys = computed(() => {
  const currentStatus = status.value
  if (!currentStatus || currentStatus.env_exists) return []

  return currentStatus.env_template
    .filter((item) => item.required)
    .map((item) => item.key)
    .filter((key) => (envValues.value[key] ?? '').trim().length === 0)
})

type DatabaseMode = 'sqlite' | 'mysql'
type StepState = 'done' | 'active' | 'pending'
type InstallStep = 'env' | 'admin' | 'done'

function resolveDatabaseMode(rawUrl: string): DatabaseMode {
  return rawUrl.trim().toLowerCase().startsWith('mysql') ? 'mysql' : 'sqlite'
}

function defaultDatabaseUrlForMode(mode: DatabaseMode): string {
  return mode === 'mysql' ? MYSQL_DATABASE_URL : SQLITE_DATABASE_URL
}

const databaseUrlDrafts = ref<Record<DatabaseMode, string>>({
  sqlite: SQLITE_DATABASE_URL,
  mysql: MYSQL_DATABASE_URL
})

const databaseMode = computed<DatabaseMode>(() =>
  resolveDatabaseMode(envValues.value.DATABASE_URL ?? SQLITE_DATABASE_URL)
)

const databaseUrlPlaceholder = computed(() =>
  databaseMode.value === 'mysql' ? MYSQL_DATABASE_URL : SQLITE_DATABASE_URL
)

const stepStates = computed<{ env: StepState; admin: StepState }>(() => {
  const currentStatus = status.value
  if (!currentStatus) {
    return { env: 'pending', admin: 'pending' }
  }

  const env: StepState = currentStatus.env_exists ? 'done' : 'active'
  let admin: StepState = 'pending'
  if (currentStatus.admin_exists) {
    admin = 'done'
  } else if (currentStatus.env_exists) {
    admin = 'active'
  }
  return { env, admin }
})

const currentStep = computed<InstallStep>(() => {
  const currentStatus = status.value
  if (!currentStatus) return 'env'
  if (!currentStatus.env_exists) return 'env'
  if (!currentStatus.admin_exists) return 'admin'
  return 'done'
})

const isEnvStep = computed(() => currentStep.value === 'env')
const isAdminStep = computed(() => currentStep.value === 'admin')

function stepStateLabel(state: StepState): string {
  if (state === 'done') return '已完成'
  if (state === 'active') return '进行中'
  return '待完成'
}

const submitButtonLabel = computed(() => {
  if (isEnvStep.value) return '保存配置并继续'
  if (isAdminStep.value) return '创建管理员并完成安装'
  return '安装已完成'
})

const showRestartCard = computed(() => {
  const currentStatus = status.value
  if (currentStatus?.restart_required) return true
  if (currentStatus && !currentStatus.restart_required && currentStatus.env_exists) return false
  return restartRequired.value
})

const effectiveRestartMessage = computed(() => {
  return restartMessage.value || status.value?.restart_message || ''
})

const passwordMismatch = computed(() => {
  const currentStatus = status.value
  if (!currentStatus || currentStatus.admin_exists) return false
  if (!adminPasswordConfirm.value) return false
  return adminPassword.value !== adminPasswordConfirm.value
})

const canSubmit = computed(() => {
  if (!status.value) return false
  if (currentStep.value === 'done') return false

  if (isEnvStep.value && missingRequiredEnvKeys.value.length > 0) {
    return false
  }

  if (isAdminStep.value) {
    if (!adminEmail.value.trim()) return false
    if (!adminPassword.value) return false
    if (!adminPasswordConfirm.value) return false
    if (passwordMismatch.value) return false
  }

  return true
})

function setError(message: string) {
  errorMessage.value = message
}

function clearError() {
  errorMessage.value = ''
}

function canGenerateSecret(key: string): boolean {
  return RANDOM_SECRET_KEYS.has(key)
}

function createRandomSecret(length = 64): string {
  if (!globalThis.crypto || typeof globalThis.crypto.getRandomValues !== 'function') {
    throw new Error('当前浏览器不支持安全随机数，请手动填写密钥')
  }
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
  const random = new Uint8Array(length)
  globalThis.crypto.getRandomValues(random)
  return Array.from(random, (value) => alphabet[value % alphabet.length]).join('')
}

function resolveInitialEnvValue(item: InstallEnvItem): string {
  if (!canGenerateSecret(item.key)) return item.default_value
  try {
    return createRandomSecret()
  } catch {
    return item.default_value
  }
}

function handleGenerateSecret(key: string) {
  try {
    envValues.value[key] = createRandomSecret()
  } catch (error: unknown) {
    setError(extractErrorMessage(error, '随机生成密钥失败'))
  }
}

function handleDatabaseModeChange(event: Event) {
  const target = event.target as { value?: unknown } | null
  const rawValue = target?.value
  const nextModeRaw = Array.isArray(rawValue) ? String(rawValue[0] ?? 'sqlite') : String(rawValue ?? 'sqlite')
  const nextMode: DatabaseMode = nextModeRaw === 'mysql' ? 'mysql' : 'sqlite'

  const currentUrl = envValues.value.DATABASE_URL ?? ''
  const currentMode = resolveDatabaseMode(currentUrl || SQLITE_DATABASE_URL)
  if (currentUrl.trim()) {
    databaseUrlDrafts.value[currentMode] = currentUrl
  }

  const nextUrl = databaseUrlDrafts.value[nextMode] || defaultDatabaseUrlForMode(nextMode)
  databaseUrlDrafts.value[nextMode] = nextUrl
  envValues.value.DATABASE_URL = nextUrl
}

async function loadStatus(options: { preserveRestartView?: boolean; silentError?: boolean } = {}) {
  isLoading.value = true
  if (!options.silentError) {
    clearError()
  }
  if (!options.preserveRestartView) {
    restartRequired.value = false
    restartMessage.value = ''
    restartPollTimedOut.value = false
  }

  try {
    const installStatus = await fetchInstallContext({ force: true })
    status.value = installStatus

    if (installStatus.restart_required) {
      restartRequired.value = true
      restartMessage.value = installStatus.restart_message || restartMessage.value
    } else {
      restartRequired.value = false
      restartMessage.value = ''
    }

    if (!installStatus.needs_install) {
      void router.replace('/login')
      return
    }

    showAdvanced.value = false
    if (!installStatus.env_exists) {
      const nextEnvValues: Record<string, string> = {}
      for (const item of installStatus.env_template) {
        nextEnvValues[item.key] = resolveInitialEnvValue(item)
      }
      const initialDatabaseUrl = nextEnvValues.DATABASE_URL?.trim()
        ? nextEnvValues.DATABASE_URL
        : SQLITE_DATABASE_URL
      nextEnvValues.DATABASE_URL = initialDatabaseUrl
      envValues.value = nextEnvValues

      const initialMode = resolveDatabaseMode(initialDatabaseUrl)
      databaseUrlDrafts.value = {
        sqlite: initialMode === 'sqlite' ? initialDatabaseUrl : SQLITE_DATABASE_URL,
        mysql: initialMode === 'mysql' ? initialDatabaseUrl : MYSQL_DATABASE_URL
      }
    }
  } catch (error: unknown) {
    if (!options.silentError) {
      setError(extractErrorMessage(error, '加载安装状态失败'))
    }
  } finally {
    isLoading.value = false
  }
}

async function handleSubmit() {
  if (!status.value || !canSubmit.value || isSubmitting.value) return

  clearError()
  isSubmitting.value = true
  const submittingStep = currentStep.value

  try {
    const payload: {
      env_values: Record<string, string>
      admin_email?: string
      admin_password?: string
    } = {
      env_values: submittingStep === 'env' ? envValues.value : {}
    }

    if (submittingStep === 'admin') {
      payload.admin_email = adminEmail.value.trim()
      payload.admin_password = await sha256Hex(adminPassword.value)
    }

    const setupResp = await runInstallSetup(payload)
    if (setupResp.restart_required || setupResp.env_created) {
      restartRequired.value = true
      restartMessage.value = setupResp.message
      restartPollTimedOut.value = false
      return
    }

    const nextStatus = await fetchInstallContext({ force: true })

    snackbar({
      message: setupResp.message,
      closeable: true
    })

    if (!nextStatus.needs_install) {
      await router.replace('/login')
      return
    }

    status.value = nextStatus
  } catch (error: unknown) {
    setError(extractErrorMessage(error, '安装失败'))
  } finally {
    isSubmitting.value = false
  }
}

function stopRestartPolling(options: { resetHintState?: boolean } = {}) {
  const { resetHintState = true } = options
  isRestartPolling.value = false

  if (resetHintState) {
    showManualRestartHint.value = false
    restartPollTimedOut.value = false
  }

  if (restartPollTimer !== null) {
    window.clearTimeout(restartPollTimer)
    restartPollTimer = null
  }

  if (restartHintTimer !== null) {
    window.clearTimeout(restartHintTimer)
    restartHintTimer = null
  }

  if (restartTimeoutTimer !== null) {
    window.clearTimeout(restartTimeoutTimer)
    restartTimeoutTimer = null
  }
}

function handleRestartPollingTimeout() {
  if (!isRestartPolling.value) return
  stopRestartPolling({ resetHintState: false })
  restartPollTimedOut.value = true
  showManualRestartHint.value = true
  setError('自动检测超过 1 分钟仍未完成，请手动重启服务端后重新检测。')
}

function scheduleRestartPolling(delay = RESTART_POLL_INTERVAL_MS) {
  if (!isRestartPolling.value || restartPollTimer !== null) return
  restartPollTimer = window.setTimeout(() => {
    restartPollTimer = null
    void pollRestartStatus()
  }, delay)
}

async function pollRestartStatus() {
  if (!isRestartPolling.value) return
  await loadStatus({ preserveRestartView: true, silentError: true })
  if (!isRestartPolling.value) return

  if (!showRestartCard.value) {
    stopRestartPolling()
    return
  }

  scheduleRestartPolling()
}

function startRestartPolling() {
  if (isRestartPolling.value) return
  isRestartPolling.value = true
  showManualRestartHint.value = false
  restartPollTimedOut.value = false

  restartHintTimer = window.setTimeout(() => {
    showManualRestartHint.value = true
  }, RESTART_MANUAL_HINT_MS)

  restartTimeoutTimer = window.setTimeout(() => {
    handleRestartPollingTimeout()
  }, RESTART_POLL_TIMEOUT_MS)

  scheduleRestartPolling(0)
}

async function handleRestartCheck() {
  restartPollTimedOut.value = false
  showManualRestartHint.value = false
  await loadStatus({ preserveRestartView: true })
  if (showRestartCard.value) {
    startRestartPolling()
  }
}

watch(
  showRestartCard,
  (visible) => {
    if (visible) {
      startRestartPolling()
      return
    }
    stopRestartPolling()
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  stopRestartPolling()
})

void loadStatus()
</script>

<style scoped>
.install-page {
  min-height: 100%;
  box-sizing: border-box;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 24px 0;
}

.install-card-wrapper {
  width: 100%;
  max-width: 860px;
  padding: 0 16px;
  margin: 0 auto;
}

.install-card {
  display: block;
  width: 100%;
  padding: 24px;
  box-sizing: border-box;
}

.restart-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.install-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.install-subtitle {
  margin: 6px 0 14px;
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.steps {
  margin: 10px 0 18px;
  display: grid;
  grid-template-columns: minmax(40px, 1fr) auto minmax(48px, 1fr) auto minmax(40px, 1fr);
  grid-template-areas:
    'connector-head node-start connector-mid node-end connector-tail'
    '. content-start . content-end .';
  column-gap: 12px;
  row-gap: 8px;
  align-items: center;
}

.step-node {
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-node-start {
  grid-area: node-start;
}

.step-node-end {
  grid-area: node-end;
}

.step-circle {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  border: 1px solid rgb(var(--mdui-color-outline));
  font-size: 13px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface));
  background: rgb(var(--mdui-color-surface-container));
}

.step-node.is-done .step-circle {
  color: rgb(var(--mdui-color-on-primary));
  background: rgb(var(--mdui-color-primary));
  border-color: rgb(var(--mdui-color-primary));
}

.step-node.is-active .step-circle {
  color: rgb(var(--mdui-color-primary));
  background: rgba(var(--mdui-color-primary), 0.14);
  border-color: rgba(var(--mdui-color-primary), 0.45);
}

.step-connector {
  width: 100%;
  height: 2px;
  border-radius: 999px;
  background: rgba(var(--mdui-color-outline), 0.45);
}

.step-connector-head {
  grid-area: connector-head;
}

.step-connector-mid {
  grid-area: connector-mid;
}

.step-connector-tail {
  grid-area: connector-tail;
}

.step-connector.done {
  background: rgba(var(--mdui-color-primary), 0.75);
}

.step-content {
  min-width: 0;
}

.step-content-start {
  grid-area: content-start;
  justify-self: center;
  text-align: center;
}

.step-content-end {
  grid-area: content-end;
  justify-self: center;
  text-align: center;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
}

.step-subtitle {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.error-banner {
  margin: 8px 0 14px;
  border: 1px solid rgb(var(--mdui-color-error));
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  color: rgb(var(--mdui-color-on-error-container));
  background: rgb(var(--mdui-color-error-container));
}

.install-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.step-hint {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.env-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-title {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.env-grid {
  display: grid;
  gap: 10px;
}

.env-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.advanced-toggle {
  width: 100%;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
  border: 1px solid rgb(var(--mdui-color-outline-variant));
  border-radius: 10px;
  padding: 10px 12px;
  background: rgb(var(--mdui-color-surface-container-low));
  color: rgb(var(--mdui-color-primary));
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
}

.advanced-toggle:hover:not(:disabled) {
  border-color: rgba(var(--mdui-color-primary), 0.45);
  background: rgba(var(--mdui-color-primary), 0.05);
}

.advanced-toggle:disabled {
  opacity: 0.72;
  cursor: default;
}

.advanced-toggle-chevron {
  width: 8px;
  height: 8px;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
  transition: transform 160ms ease;
}

.advanced-toggle.open .advanced-toggle-chevron {
  transform: rotate(225deg);
}

.advanced-config {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.random-secret-icon {
  --mdui-comp-button-icon-state-layer-color: var(--mdui-color-primary);
}

.database-mode-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.database-mode-label {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.env-comment {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
  white-space: pre-wrap;
}

.required-hint {
  font-size: 12px;
  color: rgb(var(--mdui-color-error));
}

.field-error {
  font-size: 12px;
  color: rgb(var(--mdui-color-error));
}

.restart-banner {
  border: 1px solid rgb(var(--mdui-color-primary));
  border-radius: 10px;
  padding: 12px;
  background: rgba(var(--mdui-color-primary), 0.08);
}

.restart-banner-title {
  font-size: 15px;
  font-weight: 600;
}

.restart-loading-row {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.restart-loading-text {
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.restart-banner-detail {
  margin-top: 6px;
  font-size: 13px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.restart-timeout-hint {
  margin-top: 6px;
  font-size: 13px;
  font-weight: 500;
  color: rgb(var(--mdui-color-error));
}

.submit-button {
  width: 100%;
}

@media (max-width: 640px) {
  .steps {
    grid-template-columns: minmax(16px, 1fr) auto minmax(24px, 1fr) auto minmax(16px, 1fr);
    grid-template-areas:
      'connector-head node-start connector-mid node-end connector-tail'
      '. content-start . content-end .';
    column-gap: 8px;
    row-gap: 6px;
  }
}
</style>
