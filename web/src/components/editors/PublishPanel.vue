<template>
  <div class="publish-panel">
    <div class="panel-header">
      <div class="panel-title">Paste 已创建</div>
      <div class="panel-status" :data-kind="statusKind">
        <mdui-icon v-if="statusKind === 'saving'" name="autorenew" class="status-icon spinning"></mdui-icon>
        <mdui-icon v-else-if="statusKind === 'saved'" name="check_circle"></mdui-icon>
        <mdui-icon v-else-if="statusKind === 'error'" name="error"></mdui-icon>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </div>

    <div class="info-section">
      <mdui-text-field
        label="分享链接"
        readonly
        :value="pasteUrl"
        variant="outlined"
        class="full-width"
      >
        <mdui-button-icon
          slot="suffix"
          icon="content_copy"
          :disabled="!pasteUrl"
          @click="copyToClipboard(pasteUrl, '分享链接已复制')"
        ></mdui-button-icon>
      </mdui-text-field>

      <mdui-text-field
        label="Admin Key (请妥善保管)"
        readonly
        :value="adminKey"
        variant="outlined"
        class="full-width"
      >
        <mdui-button-icon
          slot="suffix"
          icon="content_copy"
          :disabled="!adminKey"
          @click="copyToClipboard(adminKey, 'Admin Key 已复制')"
        ></mdui-button-icon>
      </mdui-text-field>
    </div>

    <div class="advanced-section">
      <div class="section-title">高级设置</div>

      <mdui-text-field
        :value="localAccessKey"
        @input="handleAccessKeyInput"
        label="访问密钥"
        type="password"
        placeholder="留空表示无需密钥"
        variant="outlined"
        clearable
        maxlength="72"
        :disabled="!isReady"
        class="full-width"
      ></mdui-text-field>

      <div class="expire-row">
        <div class="expire-label">过期时间</div>
        <mdui-segmented-button-group
          :value="localExpireTime"
          @change="handleExpireTimeChange"
          selects="single"
          required
          :disabled="!isReady"
        >
          <mdui-segmented-button value="7d">7天</mdui-segmented-button>
          <mdui-segmented-button value="30d">30天</mdui-segmented-button>
          <mdui-segmented-button value="1y">1年</mdui-segmented-button>
          <mdui-segmented-button value="never">永久</mdui-segmented-button>
        </mdui-segmented-button-group>
      </div>

      <div class="maxviews-row">
        <div class="maxviews-label">最大查看次数</div>
        <mdui-segmented-button-group
          :value="maxViewsMode"
          @change="handleMaxViewsModeChange"
          selects="single"
          required
          :disabled="!isReady"
        >
          <mdui-segmented-button value="unlimited">无限制</mdui-segmented-button>
          <mdui-segmented-button value="10">10次</mdui-segmented-button>
          <mdui-segmented-button value="100">100次</mdui-segmented-button>
          <mdui-segmented-button value="burn">阅后即焚</mdui-segmented-button>
          <mdui-segmented-button value="custom">手动输入</mdui-segmented-button>
        </mdui-segmented-button-group>

        <div v-if="maxViewsMode === 'custom'" class="maxviews-custom">
          <mdui-text-field
            :value="customMaxViewsInput"
            @input="handleCustomMaxViewsInput"
            label="自定义次数"
            type="number"
            variant="outlined"
            min="1"
            step="1"
            placeholder="请输入 >= 1 的整数"
            :disabled="!isReady"
            class="full-width"
          ></mdui-text-field>
          <div v-if="customMaxViewsError" class="field-error">{{ customMaxViewsError }}</div>
        </div>
      </div>
    </div>

    <div class="panel-actions">
      <mdui-button variant="text" @click="$emit('edit')">编辑</mdui-button>
      <mdui-button variant="tonal" @click="$emit('new')">新建</mdui-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/icon.js'
import 'mdui/components/segmented-button-group.js'
import 'mdui/components/segmented-button.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import { updatePaste } from '../../services/paste'

type ExpireTime = '7d' | '30d' | '1y' | 'never'
type PasteType = 'txt' | 'md'

const props = defineProps<{
  visible: boolean
  pasteId: string
  adminKey: string
  pasteUrl: string
  title: string
  type: PasteType
  expireTime: ExpireTime
  accessKey: string
  maxViews: number
}>()

const emit = defineEmits<{
  (e: 'update:expireTime', value: ExpireTime): void
  (e: 'update:accessKey', value: string): void
  (e: 'update:maxViews', value: number): void
  (e: 'edit'): void
  (e: 'new'): void
}>()

const localExpireTime = ref<ExpireTime>(props.expireTime)
const localAccessKey = ref(props.accessKey)
const localMaxViews = ref<number>(props.maxViews)
const customMaxViewsInput = ref<string>('')
const customMaxViewsError = ref<string>('')
const isReady = ref(false)

type MaxViewsMode = 'unlimited' | '10' | '100' | 'burn' | 'custom'
const maxViewsMode = ref<MaxViewsMode>('unlimited')

function getEventValue(e: Event): string {
  const target = e.target as
    | HTMLInputElement
    | HTMLTextAreaElement
    | { value?: unknown }
    | null
    | undefined
  const value = (target as any)?.value
  if (Array.isArray(value)) return value.join(',')
  return value == null ? '' : String(value)
}

watch(
  () => [props.pasteId, props.expireTime, props.accessKey, props.maxViews] as const,
  ([pasteId, expireTime, accessKey, maxViews]) => {
    if (!pasteId) return
    localExpireTime.value = expireTime
    localAccessKey.value = accessKey
    localMaxViews.value = maxViews
    if (maxViewsMode.value !== 'custom') {
      syncMaxViewsModeFromValue()
    }
  }
)

const saveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const saveError = ref('')
let saveTimer: number | null = null
let saveSeq = 0
let savedTimer: number | null = null

const canSave = computed(() => props.visible && !!props.pasteId && !!props.adminKey)

const statusKind = computed(() => (saveState.value === 'idle' ? 'idle' : saveState.value))
const statusText = computed(() => {
  if (!canSave.value) return ''
  if (saveState.value === 'saving') return '正在保存…'
  if (saveState.value === 'saved') return '已保存'
  if (saveState.value === 'error') return saveError.value || '保存失败'
  return ''
})

function clearTimers() {
  if (saveTimer) window.clearTimeout(saveTimer)
  if (savedTimer) window.clearTimeout(savedTimer)
  saveTimer = null
  savedTimer = null
}

async function copyToClipboard(text: string, successMessage: string) {
  try {
    await navigator.clipboard.writeText(text)
    snackbar({ message: successMessage })
  } catch (err) {
    console.error('Failed to copy: ', err)
    snackbar({ message: '复制失败', closeable: true })
  }
}

function scheduleSave() {
  if (!canSave.value) return
  if (saveTimer) window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => void saveNow(), 600)
}

async function saveNow() {
  if (!canSave.value) return

  const seq = ++saveSeq
  saveState.value = 'saving'
  saveError.value = ''

  try {
    if (localMaxViews.value !== -1 && localMaxViews.value < 1) {
      throw new Error('最大查看次数必须为 -1（无限制）或 >= 1 的整数')
    }
    await updatePaste(props.pasteId, props.adminKey, {
      expire_time: localExpireTime.value,
      max_views: localMaxViews.value,
      access_key: localAccessKey.value
    })

    if (seq !== saveSeq) return
    saveState.value = 'saved'
    if (savedTimer) window.clearTimeout(savedTimer)
    savedTimer = window.setTimeout(() => {
      if (saveState.value === 'saved') saveState.value = 'idle'
    }, 1200)
  } catch (error) {
    if (seq !== saveSeq) return
    console.error('保存设置失败:', error)
    saveState.value = 'error'
    saveError.value = error instanceof Error ? error.message : '未知错误'
  }
}

function handleExpireTimeChange(e: Event) {
  const raw = getEventValue(e)
  if (!raw) return
  if (!['7d', '30d', '1y', 'never'].includes(raw)) return
  const next = raw as ExpireTime
  localExpireTime.value = next
  emit('update:expireTime', next)
  scheduleSave()
}

function handleAccessKeyInput(e: Event) {
  const next = getEventValue(e)
  localAccessKey.value = next
  emit('update:accessKey', next)
  scheduleSave()
}

function syncMaxViewsModeFromValue() {
  const v = localMaxViews.value
  if (v === -1) {
    maxViewsMode.value = 'unlimited'
    customMaxViewsInput.value = ''
    return
  }
  if (v === 10) {
    maxViewsMode.value = '10'
    customMaxViewsInput.value = ''
    return
  }
  if (v === 100) {
    maxViewsMode.value = '100'
    customMaxViewsInput.value = ''
    return
  }
  if (v === 1) {
    maxViewsMode.value = 'burn'
    customMaxViewsInput.value = ''
    return
  }
  maxViewsMode.value = 'custom'
  customMaxViewsInput.value = customMaxViewsInput.value || String(v)
}

function handleMaxViewsModeChange(e: Event) {
  const raw = getEventValue(e)
  if (!raw) return
  if (!['unlimited', '10', '100', 'burn', 'custom'].includes(raw)) return
  const next = raw as MaxViewsMode
  maxViewsMode.value = next

  if (next === 'unlimited') {
    localMaxViews.value = -1
    customMaxViewsInput.value = ''
    customMaxViewsError.value = ''
  } else if (next === '10') {
    localMaxViews.value = 10
    customMaxViewsInput.value = ''
    customMaxViewsError.value = ''
  } else if (next === '100') {
    localMaxViews.value = 100
    customMaxViewsInput.value = ''
    customMaxViewsError.value = ''
  } else if (next === 'burn') {
    localMaxViews.value = 1
    customMaxViewsInput.value = ''
    customMaxViewsError.value = ''
  } else if (next === 'custom') {
    // 展开输入框时保持为空，不自动填充、不自动同步到预设选项。
    customMaxViewsInput.value = ''
    customMaxViewsError.value = ''
    return
  }

  emit('update:maxViews', localMaxViews.value)
  scheduleSave()
}

function handleCustomMaxViewsInput(e: Event) {
  const next = getEventValue(e)
  customMaxViewsInput.value = next
  const trimmed = next.trim()
  if (!trimmed) {
    customMaxViewsError.value = ''
    return
  }
  const parsed = Number(trimmed)
  if (!Number.isFinite(parsed)) {
    customMaxViewsError.value = '请输入 >= 1 的整数'
    return
  }
  const intVal = Math.trunc(parsed)
  if (intVal < 1) {
    customMaxViewsError.value = '请输入 >= 1 的整数'
    return
  }
  customMaxViewsError.value = ''
  localMaxViews.value = intVal
  emit('update:maxViews', localMaxViews.value)
  scheduleSave()
}

watch(
  () => props.visible,
  async (v) => {
    if (!v) {
      clearTimers()
      saveState.value = 'idle'
      saveError.value = ''
      isReady.value = false
      customMaxViewsError.value = ''
      return
    }
    isReady.value = false
    await nextTick()
    isReady.value = true
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  clearTimers()
})

syncMaxViewsModeFromValue()
</script>

<style scoped>
.publish-panel {
  background: rgb(var(--mdui-color-background));
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--mdui-color-outline-variant);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--mdui-color-on-surface);
}

.panel-status {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  color: var(--mdui-color-on-surface-variant);
  font-size: 13px;
  min-height: 20px;
  flex: 1 1 auto;
  min-width: 0;
  text-align: right;
}

.panel-status[data-kind='error'] {
  color: var(--mdui-color-error);
}

.status-icon {
  font-size: 18px;
}

.status-text {
  overflow-wrap: anywhere;
}

.spinning {
  animation: spinning 0.9s linear infinite;
}

@keyframes spinning {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.info-section {
  display: grid;
  gap: 12px;
  margin-bottom: 16px;
}

.advanced-section {
  display: grid;
  gap: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--mdui-color-on-surface);
}

.expire-row {
  display: grid;
  gap: 8px;
}

.expire-label {
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.maxviews-row {
  display: grid;
  gap: 8px;
}

.maxviews-label {
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
}

.maxviews-custom {
  margin-top: 4px;
}

.field-error {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--mdui-color-error);
}

.panel-actions {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.full-width {
  width: 100%;
}
</style>
