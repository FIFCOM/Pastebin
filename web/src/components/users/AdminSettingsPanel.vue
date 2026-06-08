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
              <div class="user-panel-meta">
                <span class="user-panel-meta-item">默认 {{ formatSettingValue(setting.default_value, setting) }}</span>
                <span v-if="setting.max_value !== null" class="user-panel-meta-item">
                  范围 {{ setting.min_value.toLocaleString() }} - {{ setting.max_value.toLocaleString() }}
                </span>
                <span v-else class="user-panel-meta-item">最小 {{ setting.min_value.toLocaleString() }}</span>
              </div>
            </div>

            <div class="setting-control">
              <mdui-text-field
                :model-value="drafts[setting.key] ?? ''"
                :label="setting.unit"
                type="number"
                variant="outlined"
                inputmode="numeric"
                :min="String(setting.min_value)"
                :max="setting.max_value === null ? undefined : String(setting.max_value)"
                :disabled="isSaving"
                :error="Boolean(validationErrors[setting.key])"
                :error-text="validationErrors[setting.key] ?? ''"
                @input="handleDraftInput(setting.key, $event)"
              ></mdui-text-field>
              <div class="setting-value-preview">{{ previewValue(setting) }}</div>
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
import { humanSize } from '../../utils/format'
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
  settings.value.some((setting) => Number.parseInt(drafts.value[setting.key] ?? '', 10) !== setting.value)
)
const canSave = computed(() => canAccess.value && hasChanges.value && !hasValidationErrors.value && !isLoading.value && !isSaving.value)
const canResetDefaults = computed(() => canAccess.value && settings.value.length > 0 && !isLoading.value && !isSaving.value)

function setDrafts(nextSettings: RuntimeSettingItem[]) {
  const nextDrafts: Partial<Record<RuntimeSettingKey, string>> = {}
  for (const setting of nextSettings) {
    nextDrafts[setting.key] = String(setting.value)
  }
  drafts.value = nextDrafts
  validationErrors.value = {}
}

function validateSetting(setting: RuntimeSettingItem, rawValue: string): string {
  const trimmed = rawValue.trim()
  if (!trimmed) return '请输入整数'
  if (!/^\d+$/.test(trimmed)) return '只能输入非负整数'

  const value = Number.parseInt(trimmed, 10)
  if (!Number.isSafeInteger(value)) return '数值过大'
  if (value === 0 && !setting.allow_zero) return `必须大于等于 ${setting.min_value}`
  if (value < setting.min_value) return `必须大于等于 ${setting.min_value}`
  if (setting.max_value !== null && value > setting.max_value) return `必须小于等于 ${setting.max_value}`
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

function formatSettingValue(value: number, setting: RuntimeSettingItem): string {
  if (value === 0 && setting.allow_zero) return '不限制'
  if (isByteSetting(setting)) return `${humanSize(value)} (${value.toLocaleString()} 字节)`
  return `${value.toLocaleString()} ${setting.unit}`
}

function previewValue(setting: RuntimeSettingItem): string {
  const raw = drafts.value[setting.key] ?? ''
  const error = validateSetting(setting, raw)
  if (error) return '等待有效数值'
  return formatSettingValue(Number.parseInt(raw, 10), setting)
}

function isChanged(setting: RuntimeSettingItem): boolean {
  const raw = drafts.value[setting.key] ?? ''
  const value = Number.parseInt(raw, 10)
  return Number.isSafeInteger(value) && value !== setting.value
}

function groupSummary(items: RuntimeSettingItem[]): string {
  return items.map((item) => `${item.label}：${previewValue(item)}`).join('；')
}

function resetToDefaults() {
  const nextDrafts: Partial<Record<RuntimeSettingKey, string>> = {}
  for (const setting of settings.value) {
    nextDrafts[setting.key] = String(setting.default_value)
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
    value: Number.parseInt(drafts.value[setting.key] ?? '', 10)
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

.setting-value-preview {
  min-height: 20px;
  font-size: 0.84rem;
  line-height: 1.45;
  color: rgb(var(--mdui-color-on-surface-variant));
}

@media (max-width: 820px) {
  .setting-item {
    grid-template-columns: 1fr;
  }
}
</style>
