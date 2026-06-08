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
              这些配置保存在数据库中，保存后立即影响新上传会话和新协作房间。
            </div>
          </div>
        </div>
      </div>

      <mdui-linear-progress v-if="isLoading || isSaving"></mdui-linear-progress>

      <div v-if="!isLoading && settings.length === 0" class="user-panel-empty-state" role="status">
        <div class="user-panel-empty-state-icon" aria-hidden="true">
          <mdui-icon name="tune"></mdui-icon>
        </div>
        <div>
          <div class="user-panel-empty-state-title">没有可展示的配置</div>
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
import 'mdui/components/text-field.js'

import { useAuth } from '../../composables/useAuth'
import {
  getAdminSettings,
  updateAdminSettings,
  type RuntimeSettingItem,
  type RuntimeSettingKey
} from '../../services/admin'
import { invalidatePublicConfigCache } from '../../services/config'
import { extractErrorMessage } from '../../utils/error'
import UserPanelCard from './UserPanelCard.vue'
import './panel.css'

type SettingGroup = {
  name: string
  items: RuntimeSettingItem[]
}

const { currentUser } = useAuth()

const settings = ref<RuntimeSettingItem[]>([])
const drafts = ref<Partial<Record<RuntimeSettingKey, string>>>({})
const validationErrors = ref<Partial<Record<RuntimeSettingKey, string>>>({})
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

const hasValidationErrors = computed(() => Object.values(validationErrors.value).some(Boolean))
const hasChanges = computed(() =>
  settings.value.some((setting) => parseDraftValue(setting, drafts.value[setting.key] ?? '') !== setting.value)
)
const canSave = computed(() => canAccess.value && hasChanges.value && !hasValidationErrors.value && !isLoading.value && !isSaving.value)
const canResetDefaults = computed(() => canAccess.value && settings.value.length > 0 && !isLoading.value && !isSaving.value)

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
  validateAll()
}

async function load() {
  if (!canAccess.value) {
    settings.value = []
    drafts.value = {}
    validationErrors.value = {}
    return
  }

  isLoading.value = true
  try {
    const response = await getAdminSettings()
    settings.value = response.settings
    setDrafts(response.settings)
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

  const payload = settings.value.map((setting) => ({
    key: setting.key,
    value: parseDraftValue(setting, drafts.value[setting.key] ?? '') ?? setting.value
  }))

  isSaving.value = true
  try {
    const response = await updateAdminSettings(payload)
    settings.value = response.settings
    setDrafts(response.settings)
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

.setting-copy {
  min-width: 0;
}

.setting-control {
  display: grid;
  gap: 8px;
}

@media (max-width: 820px) {
  .setting-item {
    grid-template-columns: 1fr;
  }
}
</style>
