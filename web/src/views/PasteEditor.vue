<template>
  <div class="paste-editor">
    <div class="editor-swap">
      <div class="editor-wrapper" :class="{ collapsed: showPublishPanel }">
        <div class="editor-inner">
          <!-- 标题输入框 -->
          <br />
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
              :readonly="showPublishPanel"
            ></mdui-text-field>
          </div>

          <!-- 内容类型选择 -->
          <div class="editor-section content-type-switch">
            <span>Markdown</span>
            <mdui-switch
              :checked="contentType === 'md'"
              @change="handleContentTypeChange"
              :disabled="showPublishPanel"
            ></mdui-switch>
            <mdui-button
              class="upload-btn"
              @click="toggleUploader"
              variant="tonal"
              :disabled="showPublishPanel"
            >
              <mdui-icon slot="icon" name="upload"></mdui-icon>
              上传文件
              <mdui-icon slot="end-icon" :name="showUploader ? 'expand_less' : 'expand_more'"></mdui-icon>
            </mdui-button>
          </div>

          <!-- 文件上传区域 -->
          <FileUploader
            ref="uploaderRef"
            :visible="showUploader && !showPublishPanel"
            :paste-id="currentPasteId"
            :admin-key="currentAdminKey"
            :encryption-key="pasteKey"
            :max-total-upload-size="maxTotalUploadSize"
            :remaining-upload-size="remainingUploadSize"
            :on-ensure-paste="ensurePasteCreated"
            @insert-file="handleInsertFile"
          />

          <!-- Plain文本输入框 -->
          <div v-show="contentType === 'txt'" class="editor-section">
            <plain-editor v-model="plainContent" @paste-files="handleMarkdownPasteFiles"></plain-editor>
          </div>

          <!-- Markdown编辑器 -->
          <div v-show="contentType === 'md'" class="editor-section">
            <markdown-editor
              v-model="markdownContent"
              @paste-files="handleMarkdownPasteFiles"
            ></markdown-editor>
          </div>

          <!-- 操作按钮 -->
          <div class="editor-actions">
            <div class="submit-wrapper" :class="{ disabled: isSubmitDisabled }" @click="handleSubmitClick">
              <mdui-button variant="filled" :disabled="isSubmitDisabled" :loading="isSubmitting">
                <mdui-icon slot="icon" name="send"></mdui-icon>
                {{ isEditingExisting ? '保存修改' : '提交' }}
              </mdui-button>
            </div>
          </div>
        </div>
      </div>

      <div class="publish-panel-wrapper" :class="{ expanded: showPublishPanel }">
        <div class="publish-panel-inner">
          <PublishPanel
            :visible="showPublishPanel"
            :paste-id="currentPasteId"
            :admin-key="currentAdminKey"
            :paste-url="pasteUrl"
            :title="title.trim()"
            :type="contentType === 'md' ? 'md' : 'txt'"
            :expire-time="expireTime"
            :access-key="accessKey"
            :max-views="maxViews"
            @update:expire-time="expireTime = $event"
            @update:access-key="accessKey = $event"
            @update:max-views="maxViews = $event"
            @edit="handleEditExisting"
            @new="handleCreateNew"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/switch.js'
import 'mdui/components/icon.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import PlainEditor from '../components/editors/Plain.vue'
import MarkdownEditor from '../components/editors/Markdown.vue'
import FileUploader from '../components/upload/FileUploader.vue'
import PublishPanel from '../components/editors/PublishPanel.vue'
import { isImageFileName } from '../composables/useFile'
import {
  generateRandomId,
  generateEncryptionKey,
  encryptContent,
  keyToUrlSafeStr
} from '../utils/crypto'
import {
  createPaste,
  uploadPasteContent,
  publishPaste,
  updatePaste
} from '../services/paste'

// 数据定义
const title = ref(`未命名的Paste.ID-${generateRandomId()}`)
const contentType = ref<'txt' | 'md'>('txt')
const plainContent = ref('')
const markdownContent = ref('')
const titleInputRef = ref<any>(null)
const isSubmitting = ref(false)
const showPublishPanel = ref(false)
const isEditingExisting = ref(false)

// Paste信息
const currentPasteId = ref('')
const currentAdminKey = ref('')
const encryptionKey = ref('')
const pasteKey = ref<Uint8Array | null>(null) // 客户端加密密钥
const maxTotalUploadSize = ref<number | null>(null)
const remainingUploadSize = ref<number | null>(null)

// 发布配置
const expireTime = ref<'7d' | '30d' | '1y' | 'never'>('30d')
const maxViews = ref(-1)
const accessKey = ref('')

// 计算属性：是否可以提交
const canSubmit = computed(() => {
  if (!title.value.trim()) return false
  
  if (contentType.value === 'txt') {
    return plainContent.value.trim().length > 0
  } else {
    return markdownContent.value.trim().length > 0
  }
})

const pasteUrl = computed(() => {
  if (!currentPasteId.value) return ''
  const baseUrl = window.location.origin
  let url = `${baseUrl}/p/${currentPasteId.value}`
  if (encryptionKey.value) {
    url += `#${encryptionKey.value}`
  }
  return url
})

// 文件上传
const showUploader = ref(false)
const uploaderRef = ref<{
  processFiles: (
    files: File[],
    opts?: { autoInsert?: boolean; source?: 'paste' | 'select' | 'drop' }
  ) => Promise<void>
  isUploading: boolean
} | null>(null)
const isUploaderUploading = computed(() => uploaderRef.value?.isUploading ?? false)
const isSubmitDisabled = computed(
  () => showPublishPanel.value || !canSubmit.value || isSubmitting.value || isUploaderUploading.value
)

const handleSubmitClick = async () => {
  if (!isSubmitDisabled.value) {
    await handleSubmit()
    return
  }
  if (isSubmitting.value) {
    snackbar({ message: '提交中，请稍候…', closeable: true })
    return
  }
  if (isUploaderUploading.value) {
    snackbar({ message: '文件上传中，请等待上传完成后再提交', closeable: true })
    return
  }
  snackbar({ message: '内容不能为空', closeable: true })
}

const toggleUploader = () => {
  if (showPublishPanel.value) return
  showUploader.value = !showUploader.value
}

const handleMarkdownPasteFiles = async (files: File[], meta?: { source: 'paste' | 'drop' }) => {
  if (!uploaderRef.value) {
    snackbar({ message: '上传组件未就绪', closeable: true })
    return
  }
  await uploaderRef.value.processFiles(files, { autoInsert: true, source: meta?.source })
}

// 确保 Paste 已创建（供文件上传使用）
const ensurePasteCreated = async (): Promise<boolean> => {
  if (currentPasteId.value && pasteKey.value) {
    return true
  }

  try {
    const createData = await createPaste('client')
    currentPasteId.value = createData.paste_id
    currentAdminKey.value = createData.admin_key
    maxTotalUploadSize.value = createData.max_total_upload_size
    remainingUploadSize.value = createData.remaining_upload_size

    const key = await generateEncryptionKey()
    pasteKey.value = key
    encryptionKey.value = keyToUrlSafeStr(key)

    return true
  } catch (error) {
    console.error('创建 Paste 失败:', error)
    snackbar({
      message: `创建失败: ${error instanceof Error ? error.message : '未知错误'}`,
      closeable: true
    })
    return false
  }
}

const handleInsertFile = (file: { fileId: string; name: string; size: number }) => {
  const fileUrl = `/api/pastes/${currentPasteId.value}/files/${file.fileId}`

  // 统一使用 Markdown 格式：图片用 ![](url)，其他用 [](url)
  const isImage = isImageFileName(file.name)
  const insertText = isImage ? `![${file.name}](${fileUrl})` : `[${file.name}](${fileUrl})`

  // 插入到当前编辑器
  if (contentType.value === 'md') {
    markdownContent.value += '\n' + insertText
  } else {
    plainContent.value += '\n' + insertText
  }
}

// 处理内容类型切换
const handleContentTypeChange = (e: Event) => {
  const target = e.target as any
  const isMarkdown = target.checked
  contentType.value = isMarkdown ? 'md' : 'txt'
  
  // 保存到 localStorage
  localStorage.setItem('content_type', contentType.value)
}

watch(contentType, (newType, oldType) => {
  if (oldType === 'md') {
    plainContent.value = markdownContent.value;
  }
  if (newType === 'md') {
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
  if (isUploaderUploading.value) {
    snackbar({ message: '文件上传中，请等待上传完成后再提交', closeable: true })
    return
  }
  
  let content = ''
  
  if (contentType.value === 'txt') {
    content = plainContent.value.trim()
  } else {
    content = markdownContent.value.trim()
  }
  
  if (!title.value.trim() || !content) {
    return
  }

  isSubmitting.value = true

  try {
    // 1. 确保 Paste 已创建（可能已通过文件上传创建）
    const ensured = await ensurePasteCreated()
    if (!ensured || !pasteKey.value) return

    // 2. 加密并上传内容
    const encryptedContent = await encryptContent(content, pasteKey.value)
    await uploadPasteContent(currentPasteId.value, currentAdminKey.value, {
      encrypted_content: encryptedContent
    })

    if (!isEditingExisting.value) {
      // 3. 立即发布，并展示发布面板
      await publishPaste(currentPasteId.value, currentAdminKey.value, {
        title: title.value.trim(),
        type: contentType.value === 'md' ? 'md' : 'txt',
        expire_time: expireTime.value,
        max_views: maxViews.value,
        access_key: accessKey.value || undefined
      })
    } else {
      // 已发布/已编辑的 Paste：通过 update 接口更新设置（避免重复 publish）
      await updatePaste(currentPasteId.value, currentAdminKey.value, {
        title: title.value.trim(),
        type: contentType.value === 'md' ? 'md' : 'txt',
        expire_time: expireTime.value,
        max_views: maxViews.value,
        access_key: accessKey.value
      })
    }

    showUploader.value = false
    showPublishPanel.value = true
    isEditingExisting.value = false
    snackbar({ message: '已保存' })
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

const handleCreateNew = () => {
  showPublishPanel.value = false
  showUploader.value = false
  isEditingExisting.value = false
  resetForm()
}

const handleEditExisting = () => {
  showPublishPanel.value = false
  showUploader.value = false
  isEditingExisting.value = true
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
  maxTotalUploadSize.value = null
  remainingUploadSize.value = null
  expireTime.value = '30d'
  maxViews.value = -1
  accessKey.value = ''
}

// 生命周期钩子
onMounted(() => {
  // 从 localStorage 中读取保存的内容类型偏好
  const savedContentType = localStorage.getItem('content_type')
  if (savedContentType === 'md' || savedContentType === 'txt') {
    contentType.value = savedContentType
  } else {
    // 如果没有保存的偏好，默认使用 txt
    contentType.value = 'txt'
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

.upload-btn {
  margin-left: auto;
}

.title-input {
  width: 100%;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid var(--mdui-color-outline-variant);
}

.submit-wrapper {
  display: inline-block;
}

.submit-wrapper.disabled {
  cursor: not-allowed;
}

.submit-wrapper.disabled :deep(mdui-button[disabled]) {
  pointer-events: none;
}

.editor-swap {
  display: grid;
  gap: 0;
}

.editor-wrapper,
.publish-panel-wrapper {
  display: grid;
  grid-template-rows: 1fr;
  transition: grid-template-rows 0.35s var(--mdui-motion-easing-standard);
  will-change: grid-template-rows;
}

.editor-wrapper.collapsed {
  grid-template-rows: 0fr;
}

.publish-panel-wrapper {
  grid-template-rows: 0fr;
}

.publish-panel-wrapper.expanded {
  grid-template-rows: 1fr;
  margin-bottom: 16px;
}

.editor-inner,
.publish-panel-inner {
  overflow: hidden;
  min-height: 0;
}

.editor-wrapper:not(.collapsed) > .editor-inner {
  overflow: visible;
}

.editor-wrapper.collapsed > .editor-inner {
  pointer-events: none;
}

.publish-panel-wrapper > .publish-panel-inner {
  pointer-events: none;
}

.publish-panel-wrapper.expanded > .publish-panel-inner {
  pointer-events: auto;
}
</style>
