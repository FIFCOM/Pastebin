<template>
  <div class="paste-editor">
      <!-- 标题输入框 -->
      <br></br>
      <div class="editor-section">
        <mdui-text-field
          ref="titleInputRef"
          v-model="title"
          label="标题"
          placeholder="请输入Paste标题"
          clearable
          variant="outlined"
          class="title-input"
          @keydown="handleTitleTabKey"
        ></mdui-text-field>
      </div>

      <!-- 内容类型选择 -->
      <div class="editor-section content-type-switch">
        <span>Markdown</span>
        <mdui-switch
          :checked="contentType === 'markdown'"
          @change="handleContentTypeChange"
        ></mdui-switch>
      </div>

      <!-- Plain文本输入框 -->
      <div v-show="contentType === 'plain'" class="editor-section">
        <plain-editor v-model="plainContent"></plain-editor>
      </div>

      <!-- Markdown编辑器 -->
      <div v-show="contentType === 'markdown'" class="editor-section">
        <markdown-editor v-model="markdownContent"></markdown-editor>
      </div>

      <!-- 操作按钮 -->
      <div class="editor-actions">
        <mdui-button
          variant="filled"
          @click="handleSubmit"
          :disabled="!canSubmit || isSubmitting"
          :loading="isSubmitting"
        >
          <mdui-icon slot="icon" name="send"></mdui-icon>
          提交
        </mdui-button>
      </div>

      <!-- 发布配置Dialog -->
      <mdui-dialog
        ref="publishConfigDialogRef"
        headline="配置发布选项"
        close-on-overlay-click
      >
        <div class="dialog-content">
          <!-- Paste信息 -->
          <div class="info-section">
            <div class="info-item">
              <span class="info-label">Paste ID:</span>
              <span class="info-value">{{ currentPasteId }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Admin Key:</span>
              <span class="info-value monospace">{{ currentAdminKey }}</span>
            </div>
          </div>

          <!-- 过期时间选择 -->
          <div class="config-section">
            <div class="config-label">过期时间</div>
            <mdui-segmented-button-group :value="expireTime" selects="single" @change="expireTime = $event.target.value">
              <mdui-segmented-button value="7d">7天</mdui-segmented-button>
              <mdui-segmented-button value="30d">30天</mdui-segmented-button>
              <mdui-segmented-button value="1y">1年</mdui-segmented-button>
              <mdui-segmented-button value="never">永久</mdui-segmented-button>
            </mdui-segmented-button-group>
          </div>

          <!-- 最大查看次数 -->
          <div class="config-section">
            <mdui-text-field
              v-model.number="maxViews"
              label="最大查看次数"
              type="number"
              helper="1表示阅后即焚，-1表示无限制"
              variant="outlined"
              min="-1"
              step="1"
            ></mdui-text-field>
          </div>

          <!-- 访问密钥（可选） -->
          <div class="config-section">
            <mdui-text-field
              v-model="accessKey"
              label="访问密钥（可选）"
              type="password"
              helper="留空则无需密钥即可访问（最多72个字符）"
              variant="outlined"
              clearable
              maxlength="72"
            ></mdui-text-field>
          </div>
        </div>

        <mdui-button slot="action" variant="text" @click="closePublishConfigDialog">取消</mdui-button>
        <mdui-button 
          slot="action" 
          variant="tonal" 
          @click="handlePublish"
          :disabled="isPublishing"
          :loading="isPublishing"
        >发布</mdui-button>
      </mdui-dialog>

      <!-- 发布成功Dialog -->
      <mdui-dialog
        ref="publishSuccessDialogRef"
        headline="发布成功"
        icon="check_circle"
        close-on-overlay-click
      >
        <div class="dialog-content">
          <div class="success-message">
            <p>您的Paste已成功发布！</p>
          </div>
          
          <div class="info-section">
            <div class="info-item">
              <span class="info-label">Paste ID:</span>
              <span class="info-value">{{ currentPasteId }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Admin Key:</span>
              <span class="info-value monospace">{{ currentAdminKey }}</span>
            </div>
            <div class="info-item" v-if="encryptionKey">
              <span class="info-label">加密密钥:</span>
              <span class="info-value monospace">{{ encryptionKey }}</span>
            </div>
          </div>

          <div class="warning-message">
            <mdui-icon name="warning"></mdui-icon>
            <p>请妥善保存以上信息，关闭后将无法再次查看！</p>
          </div>
        </div>

        <mdui-button slot="action" variant="tonal" @click="closeSuccessDialog">关闭</mdui-button>
      </mdui-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/card.js'
import 'mdui/components/switch.js'
import 'mdui/components/icon.js'
import 'mdui/components/dialog.js'
import 'mdui/components/segmented-button-group.js'
import 'mdui/components/segmented-button.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import Cookies from 'js-cookie'
import PlainEditor from './editors/Plain.vue'
import MarkdownEditor from './editors/Markdown.vue'
import {
  generateEncryptionKey,
  encryptContent,
  keyToUrlSafeStr
} from '../utils/crypto'

// 获取API基础URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 生成随机ID的函数
const generateRandomId = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < 8; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

// 数据定义
const title = ref(`未命名的Paste.ID-${generateRandomId()}`)
const contentType = ref<'plain' | 'markdown'>('plain')
const plainContent = ref('')
const markdownContent = ref('')
const titleInputRef = ref<any>(null)
const isSubmitting = ref(false)
const isPublishing = ref(false)

// Paste信息
const currentPasteId = ref('')
const currentAdminKey = ref('')
const encryptionKey = ref('')
const pasteKey = ref<Uint8Array | null>(null) // 客户端加密密钥

// 发布配置
const expireTime = ref('7d')
const maxViews = ref(-1)
const accessKey = ref('')

// Dialog引用
const publishConfigDialogRef = ref<any>(null)
const publishSuccessDialogRef = ref<any>(null)

// 计算属性：是否可以提交
const canSubmit = computed(() => {
  if (!title.value.trim()) return false
  
  if (contentType.value === 'plain') {
    return plainContent.value.trim().length > 0
  } else {
    return markdownContent.value.trim().length > 0
  }
})

// 处理内容类型切换
const handleContentTypeChange = (e: Event) => {
  const target = e.target as any
  const isMarkdown = target.checked
  contentType.value = isMarkdown ? 'markdown' : 'plain'
  
  // 保存到 Cookie
  Cookies.set('contentType', contentType.value, { expires: 30 })
}

watch(contentType, (newType, oldType) => {
  if (oldType === 'markdown') {
    plainContent.value = markdownContent.value;
  }
  if (newType === 'markdown') {
    markdownContent.value = plainContent.value;
  }
});

// 处理标题输入框的 Tab 键
const handleTitleTabKey = (e: KeyboardEvent) => {
  if (e.key === 'Tab') {
    e.preventDefault()
    insertTabInMduiField(titleInputRef, title, e.shiftKey)
  }
}

// 在 mdui-text-field 中插入 Tab 字符或取消缩进
const insertTabInMduiField = (fieldRef: any, model: any, isUnindent: boolean = false) => {
  if (!fieldRef.value) return
  
  const textField = fieldRef.value
  let input: HTMLInputElement | null = null
  
  if (textField.shadowRoot) {
    input = textField.shadowRoot.querySelector('input')
  }
  
  if (!input) {
    input = textField.querySelector('input')
  }
  
  if (input) {
    input.focus()
    const start = input.selectionStart || 0
    const end = input.selectionEnd || 0
    const value = input.value

    if (!isUnindent) {
      const newValue = value.substring(0, start) + '\t' + value.substring(end)
      
      input.value = newValue
      model.value = newValue

      const newPosition = start + 1
      input.setSelectionRange(newPosition, newPosition)

      input.dispatchEvent(new Event('input', { bubbles: true, composed: true }))
    }
  }
}

// 处理提交
const handleSubmit = async () => {
  if (!canSubmit.value || isSubmitting.value) {
    return
  }
  
  let content = ''
  
  if (contentType.value === 'plain') {
    content = plainContent.value.trim()
  } else {
    content = markdownContent.value.trim()
  }
  
  if (!title.value.trim() || !content) {
    return
  }

  isSubmitting.value = true

  try {
    // 1. 创建Paste（客户端加密模式）
    const createResponse = await fetch(`${API_BASE_URL}/api/pastes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        encryption_mode: 'client'
      })
    })

    if (!createResponse.ok) {
      throw new Error('创建Paste失败')
    }

    const createData = await createResponse.json()
    currentPasteId.value = createData.paste_id
    currentAdminKey.value = createData.admin_key

    // 2. 生成加密密钥
    const key = await generateEncryptionKey()
    pasteKey.value = key
    encryptionKey.value = keyToUrlSafeStr(key)

    // 3. 加密并上传内容
    const encryptedContent = await encryptContent(content, key)
    const contentResponse = await fetch(
      `${API_BASE_URL}/api/pastes/${currentPasteId.value}/content`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentAdminKey.value}`
        },
        body: JSON.stringify({
          encrypted_content: encryptedContent
        })
      }
    )

    if (!contentResponse.ok) {
      throw new Error('上传内容失败')
    }

    // 4. 显示发布配置Dialog
    snackbar({ message: 'Paste创建成功，请配置发布选项' })
    openPublishConfigDialog()

  } catch (error) {
    console.error('提交失败:', error)
    snackbar({ 
      message: `提交失败: ${error instanceof Error ? error.message : '未知错误'}`,
      closeable: true
    })
  } finally {
    isSubmitting.value = false
  }
}

// 打开发布配置Dialog
const openPublishConfigDialog = () => {
  if (publishConfigDialogRef.value) {
    publishConfigDialogRef.value.open = true
  }
}

// 关闭发布配置Dialog
const closePublishConfigDialog = () => {
  if (publishConfigDialogRef.value) {
    publishConfigDialogRef.value.open = false
  }
}

// 处理发布
const handlePublish = async () => {
  if (isPublishing.value) return

  isPublishing.value = true

  try {
    const publishResponse = await fetch(
      `${API_BASE_URL}/api/pastes/${currentPasteId.value}/publish`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentAdminKey.value}`
        },
        body: JSON.stringify({
          settings: {
            title: title.value.trim(),
            type: contentType.value === 'markdown' ? 'md' : 'txt',
            expire_time: expireTime.value,
            max_views: maxViews.value,
            access_key: accessKey.value || undefined
          }
        })
      }
    )

    if (!publishResponse.ok) {
      const errorData = await publishResponse.json()
      throw new Error(errorData.detail || '发布失败')
    }

    const publishData = await publishResponse.json()
    
    // 关闭配置Dialog
    closePublishConfigDialog()
    
    // 显示成功Dialog
    snackbar({ message: '发布成功！' })
    openSuccessDialog()

  } catch (error) {
    console.error('发布失败:', error)
    snackbar({ 
      message: `发布失败: ${error instanceof Error ? error.message : '未知错误'}`,
      closeable: true
    })
  } finally {
    isPublishing.value = false
  }
}

// 打开成功Dialog
const openSuccessDialog = () => {
  if (publishSuccessDialogRef.value) {
    publishSuccessDialogRef.value.open = true
  }
}

// 关闭成功Dialog
const closeSuccessDialog = () => {
  if (publishSuccessDialogRef.value) {
    publishSuccessDialogRef.value.open = false
  }
  
  // 重置表单
  resetForm()
}

// 重置表单
const resetForm = () => {
  title.value = `未命名的Paste.ID-${generateRandomId()}`
  plainContent.value = ''
  markdownContent.value = ''
  currentPasteId.value = ''
  currentAdminKey.value = ''
  encryptionKey.value = ''
  pasteKey.value = null
  expireTime.value = '7d'
  maxViews.value = -1
  accessKey.value = ''
}

// 生命周期钩子
onMounted(() => {
  // 从 Cookie 中读取保存的内容类型偏好
  const savedContentType = Cookies.get('contentType')
  if (savedContentType === 'markdown' || savedContentType === 'plain') {
    contentType.value = savedContentType
  } else {
    // 如果没有保存的偏好，默认使用 plain
    contentType.value = 'plain'
  }
})
</script>

<style scoped>
.paste-editor {
  width: 100%;
  height: 100%;
  padding: 0;
}

.editor-section {
  margin-bottom: 24px;
}

.content-type-switch {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--mdui-color-surface-variant);
  border-radius: 8px;
}

.content-type-switch > span {
  font-size: 16px;
  font-weight: 500;
  color: var(--mdui-color-on-surface);
}

.title-input {
  width: 100%;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--mdui-color-outline-variant);
}

/* Dialog样式 */
.dialog-content {
  padding: 16px 0;
}

.info-section {
  background-color: var(--mdui-color-surface-variant);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.info-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  font-weight: 500;
  color: var(--mdui-color-on-surface-variant);
  min-width: 120px;
}

.info-value {
  color: var(--mdui-color-on-surface);
  word-break: break-all;
}

.monospace {
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
}

.config-section {
  margin-bottom: 20px;
}

.config-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--mdui-color-on-surface);
  margin-bottom: 8px;
}

.success-message {
  text-align: center;
  margin-bottom: 24px;
}

.success-message p {
  font-size: 16px;
  color: var(--mdui-color-on-surface);
  margin: 0;
}

.warning-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: var(--mdui-color-error-container);
  color: var(--mdui-color-on-error-container);
  border-radius: 8px;
  margin-top: 24px;
}

.warning-message mdui-icon {
  flex-shrink: 0;
}

.warning-message p {
  margin: 0;
  font-size: 14px;
}
</style>