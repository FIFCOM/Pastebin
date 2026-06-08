<template>
  <UserPanelCard title="系统配置">
    <template #actions>
      <mdui-button variant="tonal" :disabled="!canAccess || isLoading || isSaving" :loading="isLoading" @click="load">
        刷新
      </mdui-button>
      <mdui-button variant="outlined" :disabled="!canResetDefaults" @click="resetToDefaults">
        恢复默认值
      </mdui-button>
      <mdui-button variant="filled" :disabled="!canSave" :loading="isSaving" @click="save">
        保存
      </mdui-button>
    </template>

    <div v-if="!currentUser" class="user-panel-empty-hint">请先登录。</div>
    <div v-else-if="!canAccess" class="user-panel-empty-hint">仅管理员可查看。</div>

    <div v-else class="user-panel-stack">
      <div class="user-panel-section user-panel-section--soft">
        <div class="user-panel-section-header">
          <div class="user-panel-section-heading">
            <div class="user-panel-section-eyebrow">Runtime</div>
            <div class="user-panel-section-title">运行参数</div>
            <div class="user-panel-section-copy">
              这些配置保存在数据库中，保存后立即影响新上传会话、新协作房间和邮箱验证流程。
            </div>
          </div>
        </div>
      </div>

      <mdui-linear-progress v-if="isLoading || isSaving"></mdui-linear-progress>

      <section class="user-panel-section">
        <div class="user-panel-list-header settings-group-header">
          <div>
            <div class="user-panel-list-title">邮箱验证</div>
            <div class="user-panel-list-copy">{{ emailSettingsSummary }}</div>
          </div>
          <mdui-chip v-if="hasEmailChanges" variant="filled">已修改</mdui-chip>
        </div>

        <div class="settings-grid">
          <article class="setting-item setting-item--switch">
            <div class="setting-copy">
              <div class="user-panel-row-title">启用邮箱验证码</div>
              <div class="user-panel-row-description">启用后，注册、找回密码和用户自助修改邮箱都需要邮箱验证码。</div>
            </div>
            <div class="setting-control setting-control--inline">
              <mdui-switch
                :checked="emailDraft.enabled"
                :disabled="isSaving"
                @change="handleEmailEnabledChange"
              ></mdui-switch>
            </div>
          </article>

          <template v-if="emailDraft.enabled">
            <article class="setting-item">
              <div class="setting-copy">
                <div class="user-panel-row-title">SMTP 服务器</div>
                <div class="user-panel-row-description">用于发送注册、找回密码和修改邮箱验证码。</div>
              </div>
              <div class="setting-control">
                <mdui-text-field
                  :value="emailDraft.smtp_host"
                  label="SMTP Host"
                  variant="outlined"
                  :disabled="isSaving"
                  :error="Boolean(emailErrors.smtp_host)"
                  :error-text="emailErrors.smtp_host ?? ''"
                  @input="handleEmailDraftInput('smtp_host', $event)"
                ></mdui-text-field>
              </div>
            </article>

            <article class="setting-item">
              <div class="setting-copy">
                <div class="user-panel-row-title">连接方式</div>
                <div class="user-panel-row-description">端口和加密方式按邮件服务商的 SMTP 文档填写。</div>
              </div>
              <div class="setting-control settings-two-columns">
                <mdui-text-field
                  :value="emailDraft.smtp_port"
                  label="端口"
                  type="number"
                  variant="outlined"
                  inputmode="numeric"
                  min="1"
                  max="65535"
                  step="1"
                  :disabled="isSaving"
                  :error="Boolean(emailErrors.smtp_port)"
                  :error-text="emailErrors.smtp_port ?? ''"
                  @input="handleEmailDraftInput('smtp_port', $event)"
                ></mdui-text-field>
                <mdui-select
                  :value="emailDraft.smtp_security"
                  label="安全连接"
                  variant="outlined"
                  :disabled="isSaving"
                  @change="handleSmtpSecurityChange"
                >
                  <mdui-menu-item value="starttls">STARTTLS</mdui-menu-item>
                  <mdui-menu-item value="ssl">SSL</mdui-menu-item>
                  <mdui-menu-item value="none">None</mdui-menu-item>
                </mdui-select>
              </div>
            </article>

            <article class="setting-item">
              <div class="setting-copy">
                <div class="user-panel-row-title">SMTP 认证</div>
                <div class="user-panel-row-description">密码会加密保存；留空保存会保留现有密码。</div>
              </div>
              <div class="setting-control">
                <mdui-text-field
                  :value="emailDraft.smtp_username"
                  label="用户名"
                  variant="outlined"
                  :disabled="isSaving"
                  @input="handleEmailDraftInput('smtp_username', $event)"
                ></mdui-text-field>
                <mdui-text-field
                  :value="emailDraft.smtp_password"
                  :label="emailSettings?.smtp_password_configured ? '替换密码' : '密码'"
                  type="password"
                  variant="outlined"
                  :disabled="isSaving || emailDraft.clear_smtp_password"
                  @input="handleEmailDraftInput('smtp_password', $event)"
                ></mdui-text-field>
                <div class="secret-actions">
                  <mdui-chip v-if="emailSettings?.smtp_password_configured && !emailDraft.clear_smtp_password" variant="outlined">
                    已配置密码
                  </mdui-chip>
                  <mdui-chip v-if="emailDraft.clear_smtp_password" variant="filled">
                    保存后清除密码
                  </mdui-chip>
                  <mdui-button
                    v-if="emailSettings?.smtp_password_configured"
                    variant="text"
                    :disabled="isSaving"
                    @click="toggleClearSmtpPassword"
                  >
                    {{ emailDraft.clear_smtp_password ? '保留密码' : '清除密码' }}
                  </mdui-button>
                </div>
              </div>
            </article>

            <article class="setting-item">
              <div class="setting-copy">
                <div class="user-panel-row-title">发件人</div>
                <div class="user-panel-row-description">用户收到邮件时展示的发件邮箱和名称。</div>
              </div>
              <div class="setting-control settings-two-columns">
                <mdui-text-field
                  :value="emailDraft.smtp_from_email"
                  label="发件邮箱"
                  type="email"
                  variant="outlined"
                  :disabled="isSaving"
                  :error="Boolean(emailErrors.smtp_from_email)"
                  :error-text="emailErrors.smtp_from_email ?? ''"
                  @input="handleEmailDraftInput('smtp_from_email', $event)"
                ></mdui-text-field>
                <mdui-text-field
                  :value="emailDraft.smtp_from_name"
                  label="发件名称"
                  variant="outlined"
                  :disabled="isSaving"
                  :error="Boolean(emailErrors.smtp_from_name)"
                  :error-text="emailErrors.smtp_from_name ?? ''"
                  @input="handleEmailDraftInput('smtp_from_name', $event)"
                ></mdui-text-field>
              </div>
            </article>

            <article class="setting-item">
              <div class="setting-copy">
                <div class="user-panel-row-title">验证码策略</div>
                <div class="user-panel-row-description">控制验证码有效期、重新发送间隔和错误尝试上限。</div>
              </div>
              <div class="setting-control settings-three-columns">
                <mdui-text-field
                  :value="emailDraft.code_ttl_minutes"
                  label="有效期(分钟)"
                  type="number"
                  variant="outlined"
                  inputmode="numeric"
                  min="1"
                  max="120"
                  step="1"
                  :disabled="isSaving"
                  :error="Boolean(emailErrors.code_ttl_minutes)"
                  :error-text="emailErrors.code_ttl_minutes ?? ''"
                  @input="handleEmailDraftInput('code_ttl_minutes', $event)"
                ></mdui-text-field>
                <mdui-text-field
                  :value="emailDraft.resend_interval_seconds"
                  label="重发间隔(秒)"
                  type="number"
                  variant="outlined"
                  inputmode="numeric"
                  min="10"
                  max="3600"
                  step="1"
                  :disabled="isSaving"
                  :error="Boolean(emailErrors.resend_interval_seconds)"
                  :error-text="emailErrors.resend_interval_seconds ?? ''"
                  @input="handleEmailDraftInput('resend_interval_seconds', $event)"
                ></mdui-text-field>
                <mdui-text-field
                  :value="emailDraft.max_attempts"
                  label="尝试次数"
                  type="number"
                  variant="outlined"
                  inputmode="numeric"
                  min="1"
                  max="20"
                  step="1"
                  :disabled="isSaving"
                  :error="Boolean(emailErrors.max_attempts)"
                  :error-text="emailErrors.max_attempts ?? ''"
                  @input="handleEmailDraftInput('max_attempts', $event)"
                ></mdui-text-field>
              </div>
            </article>
          </template>
        </div>
      </section>

      <div v-if="!isLoading && settings.length === 0" class="user-panel-empty-state" role="status">
        <div class="user-panel-empty-state-icon" aria-hidden="true">
          <mdui-icon name="tune"></mdui-icon>
        </div>
        <div>
          <div class="user-panel-empty-state-title">没有可展示的运行参数</div>
          <div class="user-panel-empty-state-copy">刷新后仍为空时，请检查管理员配置接口。</div>
        </div>
      </div>

      <section v-for="group in settingGroups" :key="group.name" class="user-panel-section">
        <div class="user-panel-list-header settings-group-header">
          <div>
            <div class="user-panel-list-title">{{ group.name }}</div>
            <div class="user-panel-list-copy">{{ groupSummary(group.items) }}</div>
          </div>
        </div>

        <div class="settings-grid">
          <article v-for="setting in group.items" :key="setting.key" class="setting-item">
            <div class="setting-copy">
              <div class="user-panel-row-title-row">
                <div class="user-panel-row-title">{{ setting.label }}</div>
                <mdui-chip v-if="isChanged(setting)" variant="filled">已修改</mdui-chip>
                <mdui-chip v-if="setting.allow_zero" variant="outlined">0 为不限</mdui-chip>
              </div>
              <div class="user-panel-row-description">{{ setting.description }}</div>
            </div>

            <div class="setting-control">
              <mdui-text-field
                :value="drafts[setting.key] ?? ''"
                :label="displayUnit(setting)"
                type="number"
                variant="outlined"
                :inputmode="isByteSetting(setting) ? 'decimal' : 'numeric'"
                :min="settingValueToDraft(setting.min_value, setting)"
                :max="setting.max_value === null ? undefined : settingValueToDraft(setting.max_value, setting)"
                :step="isByteSetting(setting) ? '0.000001' : '1'"
                :disabled="isSaving"
                :error="Boolean(validationErrors[setting.key])"
                :error-text="validationErrors[setting.key] ?? ''"
                @input="handleDraftInput(setting.key, $event)"
              ></mdui-text-field>
            </div>
          </article>
        </div>
      </section>
    </div>
  </UserPanelCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/button.js'
import 'mdui/components/chip.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/menu-item.js'
import 'mdui/components/select.js'
import 'mdui/components/switch.js'
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import {
  getAdminEmailSettings,
  getAdminSettings,
  updateAdminEmailSettings,
  updateAdminSettings,
  type EmailVerificationSettingsResponse,
  type EmailVerificationSettingsUpdateRequest,
  type RuntimeSettingItem,
  type RuntimeSettingKey,
  type SmtpSecurity
} from '../../services/admin'
import { invalidatePublicConfigCache } from '../../services/config'
import { extractErrorMessage } from '../../utils/error'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

type SettingGroup = {
  name: string
  items: RuntimeSettingItem[]
}

type EmailSettingsDraft = {
  enabled: boolean
  smtp_host: string
  smtp_port: string
  smtp_security: SmtpSecurity
  smtp_username: string
  smtp_password: string
  clear_smtp_password: boolean
  smtp_from_email: string
  smtp_from_name: string
  code_ttl_minutes: string
  resend_interval_seconds: string
  max_attempts: string
}

type EmailSettingsErrors = Partial<Record<keyof EmailSettingsDraft, string>>

const DEFAULT_EMAIL_SETTINGS: EmailVerificationSettingsResponse = {
  enabled: false,
  smtp_host: null,
  smtp_port: 587,
  smtp_security: 'starttls',
  smtp_username: null,
  smtp_password_configured: false,
  smtp_from_email: null,
  smtp_from_name: 'Material Bin',
  code_ttl_minutes: 10,
  resend_interval_seconds: 60,
  max_attempts: 5
}

const { currentUser } = useAuth()

const settings = ref<RuntimeSettingItem[]>([])
const drafts = ref<Partial<Record<RuntimeSettingKey, string>>>({})
const validationErrors = ref<Partial<Record<RuntimeSettingKey, string>>>({})
const emailSettings = ref<EmailVerificationSettingsResponse | null>(null)
const emailDraft = ref<EmailSettingsDraft>(settingsToEmailDraft(DEFAULT_EMAIL_SETTINGS))
const emailErrors = ref<EmailSettingsErrors>({})
const isLoading = ref(false)
const isSaving = ref(false)
const BYTES_PER_MB_BIGINT = 1024n * 1024n
const MB_SCALE_BIGINT = 1_000_000n
const MAX_SAFE_INTEGER_BIGINT = BigInt(Number.MAX_SAFE_INTEGER)

const canAccess = computed(() => currentUser.value?.role === 'admin')
const settingGroups = computed<SettingGroup[]>(() => {
  const groups = new Map<string, RuntimeSettingItem[]>()
  for (const setting of settings.value) {
    const existing = groups.get(setting.group)
    if (existing) {
      existing.push(setting)
    } else {
      groups.set(setting.group, [setting])
    }
  }
  return Array.from(groups.entries()).map(([name, items]) => ({ name, items }))
})

const hasValidationErrors = computed(() =>
  Object.values(validationErrors.value).some(Boolean) || Object.values(emailErrors.value).some(Boolean)
)
const hasRuntimeChanges = computed(() =>
  settings.value.some((setting) => parseDraftValue(setting, drafts.value[setting.key] ?? '') !== setting.value)
)
const hasEmailChanges = computed(() => isEmailDraftChanged())
const hasChanges = computed(() => hasRuntimeChanges.value || hasEmailChanges.value)
const canSave = computed(() => canAccess.value && hasChanges.value && !hasValidationErrors.value && !isLoading.value && !isSaving.value)
const canResetDefaults = computed(() => canAccess.value && (settings.value.length > 0 || emailSettings.value !== null) && !isLoading.value && !isSaving.value)
const emailSettingsSummary = computed(() => {
  if (!emailDraft.value.enabled) return '当前关闭；注册、找回密码和修改邮箱不会要求邮箱验证码。'
  const host = emailDraft.value.smtp_host.trim() || '未配置服务器'
  return `${host}；验证码 ${emailDraft.value.code_ttl_minutes || '-'} 分钟有效；重发间隔 ${emailDraft.value.resend_interval_seconds || '-'} 秒。`
})

function settingsToEmailDraft(source: EmailVerificationSettingsResponse): EmailSettingsDraft {
  return {
    enabled: source.enabled,
    smtp_host: source.smtp_host ?? '',
    smtp_port: String(source.smtp_port),
    smtp_security: source.smtp_security,
    smtp_username: source.smtp_username ?? '',
    smtp_password: '',
    clear_smtp_password: false,
    smtp_from_email: source.smtp_from_email ?? '',
    smtp_from_name: source.smtp_from_name,
    code_ttl_minutes: String(source.code_ttl_minutes),
    resend_interval_seconds: String(source.resend_interval_seconds),
    max_attempts: String(source.max_attempts)
  }
}

function setEmailDraft(nextSettings: EmailVerificationSettingsResponse) {
  emailSettings.value = nextSettings
  emailDraft.value = settingsToEmailDraft(nextSettings)
  emailErrors.value = {}
}

function normalizeString(value: string): string {
  return value.trim()
}

function parseInteger(rawValue: string): number | null {
  const trimmed = rawValue.trim()
  if (!/^\d+$/.test(trimmed)) return null
  const value = Number.parseInt(trimmed, 10)
  return Number.isSafeInteger(value) ? value : null
}

function validateIntegerField(
  errors: EmailSettingsErrors,
  key: keyof EmailSettingsDraft,
  label: string,
  min: number,
  max: number
) {
  const value = parseInteger(String(emailDraft.value[key] ?? ''))
  if (value === null) {
    errors[key] = `${label}必须是整数`
    return
  }
  if (value < min || value > max) {
    errors[key] = `${label}范围为 ${min}-${max}`
  }
}

function validateEmailSettings(): boolean {
  const errors: EmailSettingsErrors = {}
  validateIntegerField(errors, 'smtp_port', 'SMTP端口', 1, 65535)
  validateIntegerField(errors, 'code_ttl_minutes', '验证码有效期', 1, 120)
  validateIntegerField(errors, 'resend_interval_seconds', '重发间隔', 10, 3600)
  validateIntegerField(errors, 'max_attempts', '尝试次数', 1, 20)

  if (emailDraft.value.enabled) {
    if (!emailDraft.value.smtp_host.trim()) errors.smtp_host = '请输入SMTP服务器'
    if (!emailDraft.value.smtp_from_email.trim()) {
      errors.smtp_from_email = '请输入发件邮箱'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailDraft.value.smtp_from_email.trim())) {
      errors.smtp_from_email = '请输入有效邮箱'
    }
  }

  if (!emailDraft.value.smtp_from_name.trim()) {
    errors.smtp_from_name = '请输入发件名称'
  }

  emailErrors.value = errors
  return !Object.values(errors).some(Boolean)
}

function isEmailDraftChanged(): boolean {
  const source = emailSettings.value
  if (!source) return false
  const draft = emailDraft.value
  return (
    draft.enabled !== source.enabled ||
    normalizeString(draft.smtp_host) !== (source.smtp_host ?? '') ||
    parseInteger(draft.smtp_port) !== source.smtp_port ||
    draft.smtp_security !== source.smtp_security ||
    normalizeString(draft.smtp_username) !== (source.smtp_username ?? '') ||
    Boolean(draft.smtp_password) ||
    draft.clear_smtp_password ||
    normalizeString(draft.smtp_from_email) !== (source.smtp_from_email ?? '') ||
    normalizeString(draft.smtp_from_name) !== source.smtp_from_name ||
    parseInteger(draft.code_ttl_minutes) !== source.code_ttl_minutes ||
    parseInteger(draft.resend_interval_seconds) !== source.resend_interval_seconds ||
    parseInteger(draft.max_attempts) !== source.max_attempts
  )
}

function buildEmailPayload(): EmailVerificationSettingsUpdateRequest {
  return {
    enabled: emailDraft.value.enabled,
    smtp_host: normalizeString(emailDraft.value.smtp_host) || null,
    smtp_port: parseInteger(emailDraft.value.smtp_port) ?? DEFAULT_EMAIL_SETTINGS.smtp_port,
    smtp_security: emailDraft.value.smtp_security,
    smtp_username: normalizeString(emailDraft.value.smtp_username) || null,
    smtp_password: emailDraft.value.clear_smtp_password ? null : (emailDraft.value.smtp_password || null),
    clear_smtp_password: emailDraft.value.clear_smtp_password,
    smtp_from_email: normalizeString(emailDraft.value.smtp_from_email) || null,
    smtp_from_name: normalizeString(emailDraft.value.smtp_from_name) || DEFAULT_EMAIL_SETTINGS.smtp_from_name,
    code_ttl_minutes: parseInteger(emailDraft.value.code_ttl_minutes) ?? DEFAULT_EMAIL_SETTINGS.code_ttl_minutes,
    resend_interval_seconds: parseInteger(emailDraft.value.resend_interval_seconds) ?? DEFAULT_EMAIL_SETTINGS.resend_interval_seconds,
    max_attempts: parseInteger(emailDraft.value.max_attempts) ?? DEFAULT_EMAIL_SETTINGS.max_attempts
  }
}

function handleEmailEnabledChange(event: Event) {
  const target = event.target as { checked?: boolean } | null
  emailDraft.value = {
    ...emailDraft.value,
    enabled: Boolean(target?.checked)
  }
  validateEmailSettings()
}

function handleSmtpSecurityChange(event: Event) {
  const target = event.target as { value?: unknown } | null
  const value = String(target?.value ?? 'starttls')
  if (!['none', 'starttls', 'ssl'].includes(value)) return
  emailDraft.value = {
    ...emailDraft.value,
    smtp_security: value as SmtpSecurity
  }
}

function handleEmailDraftInput(key: keyof EmailSettingsDraft, event: Event) {
  const target = event.target as { value?: unknown } | null
  emailDraft.value = {
    ...emailDraft.value,
    [key]: String(target?.value ?? '')
  }
  validateEmailSettings()
}

function toggleClearSmtpPassword() {
  emailDraft.value = {
    ...emailDraft.value,
    smtp_password: '',
    clear_smtp_password: !emailDraft.value.clear_smtp_password
  }
}

function setDrafts(nextSettings: RuntimeSettingItem[]) {
  const nextDrafts: Partial<Record<RuntimeSettingKey, string>> = {}
  for (const setting of nextSettings) {
    nextDrafts[setting.key] = settingValueToDraft(setting.value, setting)
  }
  drafts.value = nextDrafts
  validationErrors.value = {}
}

function bytesToMbDraft(bytes: number): string {
  const normalized = BigInt(Math.max(0, Math.trunc(bytes)))
  const whole = normalized / BYTES_PER_MB_BIGINT
  const remainder = normalized % BYTES_PER_MB_BIGINT
  if (remainder === 0n) return whole.toString()

  let scaled = (remainder * MB_SCALE_BIGINT) / BYTES_PER_MB_BIGINT
  if (scaled === 0n) scaled = 1n

  const decimal = scaled.toString().padStart(6, '0').replace(/0+$/, '')
  return `${whole.toString()}.${decimal}`
}

function mbDraftToBytes(rawValue: string): number | null {
  const trimmed = rawValue.trim()
  if (!/^\d+(\.\d{1,6})?$/.test(trimmed)) return null

  const [wholeRaw = '0', fractionRaw = ''] = trimmed.split('.')
  const whole = BigInt(wholeRaw)
  const fraction = BigInt(fractionRaw.padEnd(6, '0'))
  const fractionBytes = (fraction * BYTES_PER_MB_BIGINT + 500_000n) / MB_SCALE_BIGINT
  const bytes = whole * BYTES_PER_MB_BIGINT + fractionBytes
  if (bytes > MAX_SAFE_INTEGER_BIGINT) return null
  return Number(bytes)
}

function parseDraftValue(setting: RuntimeSettingItem, rawValue: string): number | null {
  const trimmed = rawValue.trim()
  if (!trimmed) return null
  if (isByteSetting(setting)) return mbDraftToBytes(trimmed)
  if (!/^\d+$/.test(trimmed)) return null
  const value = Number.parseInt(trimmed, 10)
  if (!Number.isSafeInteger(value)) return null
  return value
}

function validateSetting(setting: RuntimeSettingItem, rawValue: string): string {
  const trimmed = rawValue.trim()
  if (!trimmed) return isByteSetting(setting) ? '请输入 MB 数值' : '请输入整数'
  if (isByteSetting(setting) && !/^\d+(\.\d{1,6})?$/.test(trimmed)) return '请输入非负数，最多 6 位小数'
  if (!isByteSetting(setting) && !/^\d+$/.test(trimmed)) return '只能输入非负整数'

  const value = parseDraftValue(setting, rawValue)
  if (value === null) return '数值过大'
  if (value === 0 && !setting.allow_zero) return `至少 ${formatSettingValue(setting.min_value, setting)}`
  if (value < setting.min_value) return `至少 ${formatSettingValue(setting.min_value, setting)}`
  if (setting.max_value !== null && value > setting.max_value) return '数值过大'
  return ''
}

function validateAll() {
  const nextErrors: Partial<Record<RuntimeSettingKey, string>> = {}
  for (const setting of settings.value) {
    const error = validateSetting(setting, drafts.value[setting.key] ?? '')
    if (error) nextErrors[setting.key] = error
  }
  validationErrors.value = nextErrors
  validateEmailSettings()
}

function handleDraftInput(key: RuntimeSettingKey, event: Event) {
  const target = event.target as { value?: unknown } | null
  drafts.value = {
    ...drafts.value,
    [key]: String(target?.value ?? '')
  }
  validateAll()
}

function isByteSetting(setting: RuntimeSettingItem): boolean {
  return setting.unit === '字节'
}

function displayUnit(setting: RuntimeSettingItem): string {
  return isByteSetting(setting) ? 'MB' : setting.unit
}

function settingValueToDraft(value: number, setting: RuntimeSettingItem): string {
  return isByteSetting(setting) ? bytesToMbDraft(value) : String(value)
}

function formatSettingValue(value: number, setting: RuntimeSettingItem): string {
  if (value === 0 && setting.allow_zero) return '不限制'
  if (isByteSetting(setting)) return `${bytesToMbDraft(value)} MB`
  return `${value.toLocaleString()} ${setting.unit}`
}

function previewValue(setting: RuntimeSettingItem): string {
  const raw = drafts.value[setting.key] ?? ''
  const error = validateSetting(setting, raw)
  if (error) return '等待有效数值'
  const value = parseDraftValue(setting, raw)
  return value === null ? '等待有效数值' : formatSettingValue(value, setting)
}

function isChanged(setting: RuntimeSettingItem): boolean {
  const raw = drafts.value[setting.key] ?? ''
  const value = parseDraftValue(setting, raw)
  return Number.isSafeInteger(value) && value !== setting.value
}

function groupSummary(items: RuntimeSettingItem[]): string {
  return items.map((item) => `${item.label}：${previewValue(item)}`).join('；')
}

function resetToDefaults() {
  const nextDrafts: Partial<Record<RuntimeSettingKey, string>> = {}
  for (const setting of settings.value) {
    nextDrafts[setting.key] = settingValueToDraft(setting.default_value, setting)
  }
  drafts.value = nextDrafts
  emailDraft.value = settingsToEmailDraft(DEFAULT_EMAIL_SETTINGS)
  emailDraft.value.clear_smtp_password = Boolean(emailSettings.value?.smtp_password_configured)
  validateAll()
}

async function load() {
  if (!canAccess.value) {
    settings.value = []
    drafts.value = {}
    validationErrors.value = {}
    emailSettings.value = null
    emailDraft.value = settingsToEmailDraft(DEFAULT_EMAIL_SETTINGS)
    emailErrors.value = {}
    return
  }

  isLoading.value = true
  try {
    const [runtimeResponse, emailResponse] = await Promise.all([
      getAdminSettings(),
      getAdminEmailSettings()
    ])
    settings.value = runtimeResponse.settings
    setDrafts(runtimeResponse.settings)
    setEmailDraft(emailResponse)
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '获取系统配置失败'), closeable: true })
  } finally {
    isLoading.value = false
  }
}

async function save() {
  if (!canAccess.value || isSaving.value) return

  validateAll()
  if (hasValidationErrors.value) return

  isSaving.value = true
  try {
    if (hasRuntimeChanges.value) {
      const payload = settings.value.map((setting) => ({
        key: setting.key,
        value: parseDraftValue(setting, drafts.value[setting.key] ?? '') ?? setting.value
      }))
      const response = await updateAdminSettings(payload)
      settings.value = response.settings
      setDrafts(response.settings)
    }

    if (hasEmailChanges.value) {
      const response = await updateAdminEmailSettings(buildEmailPayload())
      setEmailDraft(response)
    }

    invalidatePublicConfigCache()
    snackbar({ message: '系统配置已保存', closeable: true })
  } catch (error: unknown) {
    snackbar({ message: extractErrorMessage(error, '保存系统配置失败'), closeable: true })
  } finally {
    isSaving.value = false
  }
}

watch(
  canAccess,
  () => {
    void load()
  },
  { immediate: true }
)
</script>

<style scoped>
.settings-group-header {
  margin-bottom: 16px;
}

.settings-grid {
  display: grid;
  gap: 12px;
}

.setting-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 280px);
  gap: 18px;
  align-items: start;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.58);
  background: rgb(var(--mdui-color-surface-container-low));
}

.setting-item--switch {
  align-items: center;
}

.setting-copy {
  min-width: 0;
}

.setting-control {
  display: grid;
  gap: 8px;
}

.setting-control--inline {
  justify-items: end;
}

.settings-two-columns,
.settings-three-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.settings-three-columns {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.secret-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 900px) {
  .settings-three-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 820px) {
  .setting-item,
  .settings-two-columns {
    grid-template-columns: 1fr;
  }

  .setting-control--inline {
    justify-items: start;
  }
}
</style>
