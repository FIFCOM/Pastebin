<template>
  <div class="paste-view">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-indicator">
      <mdui-circular-progress></mdui-circular-progress>
    </div>


    <!-- Paste 内容 -->
    <div v-else-if="pasteData && decryptedContent" class="paste-content">
      <div class="paste-header">
        <mdui-tooltip :content="viewerType === 'md' ? '切换为纯文本' : '切换为 Markdown'">
          <mdui-button-icon @click="toggleViewerType">
            <mdui-icon-article v-if="viewerType === 'md'"></mdui-icon-article>
            <mdui-icon-code v-else></mdui-icon-code>
          </mdui-button-icon>
        </mdui-tooltip>
        <h1 class="mdui-typo-headline">{{ pasteTitle }}</h1>
      </div>

      <div class="paste-meta">
        <mdui-tooltip content="浏览次数">
          <span class="meta-item meta-icon"><mdui-icon-remove-red-eye></mdui-icon-remove-red-eye>{{ pasteViewsText }}</span>
        </mdui-tooltip>
        <mdui-tooltip content="创建时间">
          <span class="meta-item meta-icon"><mdui-icon-create></mdui-icon-create>{{ pasteCreatedText }}</span>
        </mdui-tooltip>
        <mdui-tooltip content="过期时间">
          <span class="meta-item meta-icon"><mdui-icon-auto-delete></mdui-icon-auto-delete>{{ pasteExpireInlineText }}</span>
        </mdui-tooltip>
        <mdui-tooltip content="文件列表">
          <button type="button" class="meta-item meta-icon meta-action" @click="openPasteFilesDialog">
            <mdui-icon-folder></mdui-icon-folder>{{ pasteFilesText }}
          </button>
        </mdui-tooltip>
      </div>

      <!-- Plain Viewer -->
      <plain-viewer v-if="viewerType === 'txt'" :content="decryptedContent" />
      
      <!-- Markdown Viewer -->
      <markdown-viewer
        v-else-if="viewerType === 'md'"
        :content="decryptedContent"
        :encryption-key="encryptionKeyBytes"
        :access-key="currentAccessKey"
      />
    </div>

    <!-- 文件列表对话框 -->
    <PasteFilesDialog
      ref="pasteFilesDialog"
      :files="pasteFiles"
      :paste-id="pasteId"
      :encryption-key="encryptionKeyBytes"
      :encryption-key-hash="encryptionKeyHash"
    />

    <!-- Access Key 输入对话框 -->
    <mdui-dialog
      ref="accessKeyDialog"
      headline="需要访问密钥"
      close-on-esc="false"
      close-on-overlay-click="false"
    >
      <mdui-icon slot="icon" name="lock" style="color: rgb(var(--mdui-color-primary));"></mdui-icon>
      <div class="dialog-content">
        <p class="dialog-description">此 Paste 受访问密钥保护，请输入密钥以查看内容。</p>
        
        <div class="config-section">
          <mdui-text-field
            v-model="accessKeyInput"
            label="访问密钥"
            placeholder="请输入访问密钥"
            type="password"
            variant="outlined"
            maxlength="72"
            counter
            @keydown.enter="handleAccessKeySubmit"
          ></mdui-text-field>
        </div>

        <div v-if="accessKeyError" class="warning-message">
          <mdui-icon name="error"></mdui-icon>
          <p>访问密钥验证失败，请重试。</p>
        </div>
      </div>
      
      <mdui-button
        slot="action"
        variant="tonal"
        @click="handleAccessKeySubmit"
        :disabled="!accessKeyInput.trim()"
      >
        确认
      </mdui-button>
    </mdui-dialog>

    <!-- 错误对话框 -->
    <mdui-dialog
      ref="errorDialog"
      headline="错误"
      close-on-esc="false"
      close-on-overlay-click="false"
    >
      <mdui-icon slot="icon" name="error" style="color: rgb(var(--mdui-color-error));"></mdui-icon>
      <div class="dialog-content">
        <p class="dialog-description">{{ error }}</p>
      </div>
    </mdui-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getPaste, getPasteContent, type PasteData, type PasteFile } from '@/services/paste'
import { decryptContent, urlSafeStrToKey } from '@/utils/crypto'
import { useTheme } from '@/composables/useTheme'
import { formatDate } from '@/utils/format'
import PlainViewer from '@/components/viewers/Plain.vue'
import PasteFilesDialog from '@/components/paste/PasteFilesDialog.vue'
import 'mdui/components/circular-progress.js'
import 'mdui/components/card.js'
import 'mdui/components/dialog.js'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/top-app-bar.js'
import 'mdui/components/tooltip.js'
import '@mdui/icons/remove-red-eye.js'
import '@mdui/icons/create.js'
import '@mdui/icons/auto-delete.js'
import '@mdui/icons/code.js'
import '@mdui/icons/article.js'
import '@mdui/icons/folder.js'

useTheme()

const MarkdownViewer = defineAsyncComponent(() => import('@/components/viewers/Markdown.vue'))

const route = useRoute()

// 状态
const pasteData = ref<PasteData | null>(null)
const pasteFiles = ref<PasteFile[]>([])
const decryptedContent = ref<string>('')
const isLoading = ref<boolean>(true)
const error = ref<string>('')
const viewerType = ref<'txt' | 'md'>('txt')
const encryptionKeyBytes = ref<Uint8Array | null>(null)

// Access Key 相关
const accessKeyDialog = ref<any>(null)
const accessKeyInput = ref<string>('')
const accessKeyError = ref<boolean>(false)
const currentAccessKey = ref<string | undefined>(undefined)

// 错误对话框
const errorDialog = ref<any>(null)
const pasteFilesDialog = ref<{ open: () => void } | null>(null)

const pasteTitle = computed(() => pasteData.value?.title || '未命名 Paste')
const pasteCreatedText = computed(() => {
  const v = pasteData.value?.published_at || pasteData.value?.updated_at
  return formatDate(v)
})
const pasteExpireInlineText = computed(() => {
  const v = pasteData.value?.expire_at ?? null
  if (!v) return '永不过期'
  return formatDate(v)
})
const pasteViewsText = computed(() => {
  const viewCount = Number(pasteData.value?.view_count)
  return Number.isFinite(viewCount) && viewCount >= 0 ? viewCount : 0
})
const pasteFilesText = computed(() => `${pasteFiles.value.length} 个文件`)
const pasteId = computed(() => String(route.params.paste_id || ''))
const encryptionKeyHash = computed(() => window.location.hash || '')

function openPasteFilesDialog() {
  pasteFilesDialog.value?.open()
}

/**
 * 显示错误对话框
 */
function showErrorDialog(errorMessage: string) {
  error.value = errorMessage
  if (errorDialog.value) {
    errorDialog.value.open = true
  }
}

/**
 * 验证必需参数
 */
function validateParams(): { pasteId: string; encryptionKey: Uint8Array } | null {
  const pasteId = route.params.paste_id as string
  if (!pasteId) {
    showErrorDialog('URL 中缺少 Paste ID。')
    return null
  }

  const encryptionKeyStr = window.location.hash.substring(1)
  if (!encryptionKeyStr) {
    showErrorDialog('URL 中缺少加密密钥（hash 部分）。')
    return null
  }

  try {
    const encryptionKey = urlSafeStrToKey(encryptionKeyStr)
    encryptionKeyBytes.value = encryptionKey
    return { pasteId, encryptionKey }
  } catch (err) {
    showErrorDialog('无效的加密密钥格式。')
    return null
  }
}

/**
 * 切换 Viewer 类型
 */
function toggleViewerType() {
  viewerType.value = viewerType.value === 'md' ? 'txt' : 'md'
}

/**
 * 加载 Paste 数据
 */
async function loadPaste(pasteId: string, encryptionKey: Uint8Array, accessKey?: string): Promise<boolean> {
  try {
    pasteFiles.value = []
    const [data, content] = await Promise.all([
      getPaste(pasteId, accessKey),
      getPasteContent(pasteId, accessKey)
    ])

    if (!content.encrypted_content) {
      throw new Error('内容为空或格式不正确')
    }

    pasteData.value = data
    pasteFiles.value = Array.isArray(content.files) ? content.files : []
    decryptedContent.value = await decryptContent(content.encrypted_content, encryptionKey)
    currentAccessKey.value = accessKey
    if (accessKey && accessKey.trim()) {
      try {
        sessionStorage.setItem(`mb_access_key:${pasteId}`, accessKey.trim())
      } catch {
        // ignore
      }
    }
    
    // 根据 paste 类型设置默认 viewer（不使用持久化）
    viewerType.value = data.type === 'md' ? 'md' : 'txt'
    
    return true
  } catch (e: any) {
    return handleLoadError(e)
  }
}

/**
 * 处理加载错误
 */
function handleLoadError(e: any): boolean {
  if (e.response) {
    const status = e.response.status
    
    if (status === 404) {
      showErrorDialog('Paste 不存在，这可能是因为 Paste ID 错误或 Paste 已被删除。')
    } else if (status === 403) {
      // 需要 access key - 返回特殊标记
      return false // 不设置错误，由调用方处理
    } else {
      showErrorDialog(`服务器错误 (${status})：${e.response.data?.message || '未知错误'}`)
    }
  } else if (e instanceof Error) {
    if (e.message.includes('decrypt') || e.name === 'OperationError') {
      showErrorDialog('解密失败，密钥可能不正确或数据已损坏。')
    } else {
      showErrorDialog(`发生错误：${e.message}`)
    }
  } else {
    showErrorDialog('发生未知错误。')
  }
  
  console.error('Load paste error:', e)
  return false
}

/**
 * 显示 Access Key 输入对话框
 */
function showAccessKeyDialog(isRetry: boolean = false) {
  isLoading.value = false
  // 重试时清空输入但保持错误状态；首次显示时清空两者
  accessKeyInput.value = ''
  if (!isRetry) {
    accessKeyError.value = false
  }
  if (accessKeyDialog.value) {
    accessKeyDialog.value.open = true
  }
}

/**
 * 处理 Access Key 提交
 */
async function handleAccessKeySubmit() {
  const params = validateParams()
  if (!params) return

  const trimmedKey = accessKeyInput.value.trim()
  if (!trimmedKey) {
    accessKeyError.value = true
    return
  }

  // 关闭对话框并重新加载
  if (accessKeyDialog.value) {
    accessKeyDialog.value.open = false
  }
  isLoading.value = true
  error.value = ''
  currentAccessKey.value = trimmedKey

  const success = await loadPaste(params.pasteId, params.encryptionKey, trimmedKey)
  
  if (!success && !error.value) {
    // 如果失败且没有其他错误（即 403），说明密钥错误
    accessKeyError.value = true
    showAccessKeyDialog(true) // 传入 true 表示是重试，不清除输入和错误状态
  }
  
  isLoading.value = false
}

/**
 * 初始化加载
 */
onMounted(async () => {
  isLoading.value = true
  error.value = ''

  const params = validateParams()
  if (!params) {
    isLoading.value = false
    return
  }

  let cachedAccessKey: string | undefined = undefined
  try {
    const cached = sessionStorage.getItem(`mb_access_key:${params.pasteId}`)
    if (cached && cached.trim()) cachedAccessKey = cached.trim()
  } catch {
    // ignore
  }

  const success = await loadPaste(params.pasteId, params.encryptionKey, cachedAccessKey)
  
  if (!success && !error.value) {
    // 首次加载时需要 access key
    showAccessKeyDialog(false)
  }
  
  isLoading.value = false
})
</script>

<style scoped>
.paste-view {
  padding-top: 0rem;
  padding-bottom: 1rem;
}

.loading-indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.paste-content {
  margin-top: 1rem;
}

.paste-header {
  margin-bottom: 4px;
}

.paste-header h1 {
  margin: 0;
  display: inline;
}

.paste-header mdui-tooltip {
  display: inline-block;
  vertical-align: top;
  margin-top: 3px;
  margin-right: 2px;
}

.paste-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 0;
  margin-bottom: 20px;
  font-size: 13px;
  color: rgb(var(--mdui-color-outline));
}

.paste-meta mdui-tooltip::after {
  content: '';
  margin: 0 8px;
  opacity: 0.5;
}

.paste-meta mdui-tooltip:last-child::after {
  display: none;
}

.paste-meta .meta-icon {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.paste-meta .meta-icon :is(mdui-icon-remove-red-eye, mdui-icon-create, mdui-icon-auto-delete, mdui-icon-folder) {
  font-size: 15px;
}

.paste-meta .meta-action {
  border: 0;
  background: transparent;
  margin: 0;
  padding: 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.paste-meta .meta-action:hover {
  color: rgb(var(--mdui-color-primary));
}

.paste-meta .meta-action:focus-visible {
  outline: 2px solid rgb(var(--mdui-color-primary));
  outline-offset: 2px;
  border-radius: 4px;
}

/* Dialog 样式 */
.dialog-content {
  padding: 16px 0;
}

.dialog-description {
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface-variant));
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.config-section {
  margin-bottom: 20px;
}

.warning-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: rgb(var(--mdui-color-error-container));
  color: rgb(var(--mdui-color-on-error-container));
  border-radius: 8px;
  margin-top: 8px;
}

.warning-message mdui-icon {
  flex-shrink: 0;
  font-size: 20px;
}

.warning-message p {
  margin: 0;
  font-size: 14px;
}
</style>
