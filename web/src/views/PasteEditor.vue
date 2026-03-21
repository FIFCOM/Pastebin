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
              :paste-id="currentPasteId"
              :encryption-key="pasteKey"
              :access-key="accessKey"
              :admin-key="currentAdminKey"
              @paste-files="handleMarkdownPasteFiles"
            ></markdown-editor>
          </div>

          <!-- 操作按钮 -->
          <div class="editor-actions">
            <mdui-button
              v-if="activeRoom"
              class="room-status-button"
              variant="tonal"
              @click="openCollabDialog"
            >
              <mdui-icon slot="icon" name="groups"></mdui-icon>
              {{ activeRoomButtonLabel }}
            </mdui-button>
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
import { useRoute, useRouter } from 'vue-router'
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
  decryptContent,
  encryptContent,
  keyToUrlSafeStr,
  urlSafeStrToKey
} from '../utils/crypto'
import { buildAbsoluteAppUrl } from '../utils/appUrl'
import {
  createPaste,
  getPaste,
  getPasteContent,
  uploadPasteContent,
  publishPaste,
  updatePaste
} from '../services/paste'
import { useAuth } from '../composables/useAuth'
import { useCollabDialogState } from '../composables/useCollabDialogState'
import { useRoomSession } from '../composables/useRoomSession'
import { useHistory } from '../composables/useHistory'

const { currentUser } = useAuth()
const { addToHistory } = useHistory()
const { openCollabDialog } = useCollabDialogState()
const { activeRoom } = useRoomSession()
const route = useRoute()
const router = useRouter()
const EDIT_CONTEXT_STORAGE_KEY = 'mb_editor_edit_context_v1'
const EDIT_CONTEXT_TTL_MS = 10 * 60 * 1000

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
  let url = buildAbsoluteAppUrl(`/p/${currentPasteId.value}`)
  if (encryptionKey.value) {
    url += `#${encryptionKey.value}`
  }
  return url
})

const activeRoomButtonLabel = computed(() => {
  if (!activeRoom.value) return ''
  const roomIdLabel = activeRoom.value.pinCode || activeRoom.value.roomId
  const joinedCount = activeRoom.value.memberCount ?? '—'
  const maxMembersText = activeRoom.value.maxMembers ?? '—'
  return `房间${roomIdLabel} ${joinedCount}/${maxMembersText}`
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
const isBootstrappingEdit = ref(false)
const isUploaderUploading = computed(() => uploaderRef.value?.isUploading ?? false)
const isSubmitDisabled = computed(
  () =>
    showPublishPanel.value ||
    !canSubmit.value ||
    isSubmitting.value ||
    isUploaderUploading.value ||
    isBootstrappingEdit.value
)

function firstQueryValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return ''
}

interface EditBootstrapContext {
  pasteId: string
  adminKey: string
  encryptionKey: string
}

function readEditContextFromStorage(expectedPasteId: string): EditBootstrapContext | null {
  let raw = ''

  try {
    raw = sessionStorage.getItem(EDIT_CONTEXT_STORAGE_KEY) || ''
    sessionStorage.removeItem(EDIT_CONTEXT_STORAGE_KEY)
  } catch {
    return null
  }

  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as {
      paste_id?: unknown
      admin_key?: unknown
      encryption_key?: unknown
      created_at?: unknown
    }

    const pasteId = typeof parsed.paste_id === 'string' ? parsed.paste_id.trim() : ''
    const adminKey = typeof parsed.admin_key === 'string' ? parsed.admin_key.trim() : ''
    const encryptionKey =
      typeof parsed.encryption_key === 'string' ? parsed.encryption_key.trim() : ''
    const createdAt =
      typeof parsed.created_at === 'number' && Number.isFinite(parsed.created_at)
        ? parsed.created_at
        : 0

    if (!pasteId || !adminKey || !encryptionKey) return null
    if (Date.now() - createdAt > EDIT_CONTEXT_TTL_MS) return null
    if (expectedPasteId && expectedPasteId !== pasteId) return null

    return { pasteId, adminKey, encryptionKey }
  } catch {
    return null
  }
}

async function preloadExistingPasteForEdit(
  pasteId: string,
  adminKey: string,
  key: Uint8Array
): Promise<void> {
  try {
    const [pasteData, contentData] = await Promise.all([
      getPaste(pasteId, undefined, adminKey),
      getPasteContent(pasteId, undefined, adminKey)
    ])

    if (typeof pasteData.title === 'string' && pasteData.title.trim()) {
      title.value = pasteData.title.trim()
    }
    contentType.value = pasteData.type === 'md' ? 'md' : 'txt'
    maxViews.value = Number.isFinite(pasteData.max_views) ? pasteData.max_views : -1

    const decryptedText =
      typeof contentData.content === 'string'
        ? contentData.content
        : contentData.encrypted_content
          ? await decryptContent(contentData.encrypted_content, key)
          : ''

    plainContent.value = decryptedText
    markdownContent.value = decryptedText
  } catch (error) {
    console.error('加载待编辑内容失败:', error)
    snackbar({ message: '已进入编辑模式，但无法自动加载原内容', closeable: true })
  }
}

async function tryBootstrapEditContextFromRoute(): Promise<void> {
  const queryPasteId = firstQueryValue(route.query.paste_id).trim()
  const storageContext = readEditContextFromStorage(queryPasteId)

  if (!queryPasteId && !storageContext) {
    return
  }

  if (!storageContext) {
    snackbar({ message: '编辑上下文已失效，请从历史记录重新进入', closeable: true })
    void router.replace({ path: '/', query: {}, hash: '' })
    return
  }

  const pasteId = storageContext.pasteId
  const adminKey = storageContext.adminKey
  const rawEncryptionKey = storageContext.encryptionKey

  if (!pasteId || !adminKey || !rawEncryptionKey) {
    snackbar({ message: '编辑参数不完整，已忽略本次编辑上下文', closeable: true })
    return
  }

  try {
    const key = urlSafeStrToKey(rawEncryptionKey)
    isBootstrappingEdit.value = true
    pasteKey.value = key
    currentPasteId.value = pasteId
    currentAdminKey.value = adminKey
    encryptionKey.value = rawEncryptionKey
    isEditingExisting.value = true
    showPublishPanel.value = false
    showUploader.value = false

    await preloadExistingPasteForEdit(pasteId, adminKey, key)

    void router.replace({ path: '/', query: {}, hash: '' })
  } catch {
    snackbar({ message: '编辑密钥无效，无法进入编辑模式', closeable: true })
  } finally {
    isBootstrappingEdit.value = false
  }
}

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
  const target = e.target as HTMLInputElement | null
  const isMarkdown = Boolean(target?.checked)
  contentType.value = isMarkdown ? 'md' : 'txt'
  
  // 保存到 localStorage
  localStorage.setItem('content_type', contentType.value)
}

watch(contentType, (newType, oldType) => {
  if (oldType === 'md') {
    plainContent.value = markdownContent.value
  }
  if (newType === 'md') {
    markdownContent.value = plainContent.value
  }
})

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
    const wasEditing = isEditingExisting.value
    const finalTitle = title.value.trim()
    // 1. 确保 Paste 已创建（可能已通过文件上传创建）
    const ensured = await ensurePasteCreated()
    if (!ensured || !pasteKey.value) return

    // 2. 加密并上传内容
    const encryptedContent = await encryptContent(content, pasteKey.value)
    await uploadPasteContent(currentPasteId.value, currentAdminKey.value, {
      encrypted_content: encryptedContent
    })

    if (!wasEditing) {
      // 3. 立即发布，并展示发布面板
      await publishPaste(currentPasteId.value, currentAdminKey.value, {
        title: finalTitle,
        type: contentType.value === 'md' ? 'md' : 'txt',
        expire_time: expireTime.value,
        max_views: maxViews.value,
        access_key: accessKey.value || undefined
      })
    } else {
      // 已发布/已编辑的 Paste：更新标题和类型，避免误覆盖高级设置。
      await updatePaste(currentPasteId.value, currentAdminKey.value, {
        title: finalTitle,
        type: contentType.value === 'md' ? 'md' : 'txt'
      })
    }

    showUploader.value = false
    showPublishPanel.value = true
    isEditingExisting.value = false
    snackbar({ message: '已保存' })
    // 保存到历史记录（游客写本地，已登录写服务端）
    void addToHistory(
      currentPasteId.value,
      currentAdminKey.value,
      encryptionKey.value,
      currentUser.value?.id ?? null,
      {
        title: finalTitle,
        status: wasEditing ? 'edited' : 'published'
      }
    )
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

  void tryBootstrapEditContextFromRoute()
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
  border-radius: 8px;
}

.content-type-switch > span {
  font-size: 16px;
  font-weight: 500;
  color: rgb(var(--mdui-color-on-surface));
}

.upload-btn {
  margin-left: auto;
}

.title-input {
  width: 100%;
}

.editor-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.room-status-button {
  margin-right: auto;
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
