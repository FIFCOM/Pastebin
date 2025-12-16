<template>
  <div class="file-uploader-wrapper" :class="{ expanded: visible }">
    <div class="file-uploader">
    <!-- 拖拽上传区域 -->
    <div
      class="drop-zone"
      :class="{ 'drag-over': isDragOver }"
      @dragenter.prevent="handleDragEnter"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <mdui-icon name="cloud_upload" class="drop-icon"></mdui-icon>
      <p>拖拽/粘贴文件到此处，或点击选择文件</p>
      <p class="hint">单个文件最大 {{ Math.round(maxFileSize / 1024 / 1024) }}MB</p>
      <input
        ref="fileInputRef"
        type="file"
        multiple
        hidden
        @change="handleFileSelect"
      />
    </div>

    <!-- 上传中的文件列表 -->
    <div v-if="uploadingFiles.length > 0" class="file-list">
      <div class="list-header">上传中</div>
      <div class="list-scroll-container">
        <mdui-list>
          <mdui-list-item
            v-for="file in uploadingFiles"
            :key="file.id"
            rounded
            nonclickable
            :headline="truncateFileName(file.name)"
            class="uploading-item"
            :style="{ '--upload-progress': file.progress + '%' }"
          >
            <mdui-circular-progress slot="icon"></mdui-circular-progress>
            <span slot="description" class="file-status">{{ file.progress }}% · {{ formatSpeed(file.speed) }}</span>
            <mdui-button-icon slot="end-icon" icon="close" @click="cancelUpload(file.id)"></mdui-button-icon>
          </mdui-list-item>
        </mdui-list>
      </div>
    </div>

    <!-- 已上传的文件列表 -->
    <div v-if="uploadedFiles.length > 0" class="file-list">
      <div class="list-header">已上传</div>
      <div class="list-scroll-container">
        <mdui-list>
          <mdui-list-item
            v-for="file in uploadedFiles"
            :key="file.id"
            rounded
            nonclickable
            icon="description"
            :headline="truncateFileName(file.name)"
          >
            <span slot="description" class="file-size">{{ formatFileSize(file.size) }}</span>
            <div slot="end-icon" class="action-buttons">
              <mdui-button-icon icon="add_link" @click="insertFile(file)"></mdui-button-icon>
              <mdui-button-icon icon="delete" @click="removeFile(file.id)"></mdui-button-icon>
            </div>
          </mdui-list-item>
        </mdui-list>
      </div>
    </div>

    <!-- 上传失败的文件 -->
    <div v-if="failedFiles.length > 0" class="file-list">
      <div class="list-header error">上传失败</div>
      <div class="list-scroll-container">
        <mdui-list>
          <mdui-list-item
            v-for="file in failedFiles"
            :key="file.id"
            rounded
            nonclickable
            :headline="truncateFileName(file.name)"
            class="failed-item"
          >
            <mdui-icon slot="icon" name="error" class="file-icon error"></mdui-icon>
            <span slot="description" class="file-error">{{ file.error }}</span>
            <div slot="end-icon" class="action-buttons">
              <mdui-button-icon icon="refresh" @click="retryUpload(file)"></mdui-button-icon>
              <mdui-button-icon icon="close" @click="dismissFailed(file.id)"></mdui-button-icon>
            </div>
          </mdui-list-item>
        </mdui-list>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import 'mdui/components/icon.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/list.js'
import 'mdui/components/list-item.js'
import 'mdui/components/circular-progress.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import {
  initFileUpload,
  uploadFileChunk,
  completeFileUpload,
  abortFileUpload,
  deleteFile
} from '../../services/paste'
import { getPublicConfig } from '../../services/config'
import {
  encryptFileChunk,
  encryptWithKey,
  bytesToStr
} from '../../utils/crypto'

interface UploadingFile {
  id: string
  name: string
  size: number
  progress: number
  speed: number // bytes per second
  file: File
  uploadId?: string
  abortController?: AbortController
}

interface UploadedFile {
  id: string
  fileId: string
  name: string
  size: number
}

interface FailedFile {
  id: string
  name: string
  size: number
  error: string
  file: File
}

const props = defineProps<{
  visible: boolean
  pasteId: string
  adminKey: string
  encryptionKey: Uint8Array | null
  onEnsurePaste: () => Promise<boolean>
}>()

const emit = defineEmits<{
  (e: 'insert-file', file: { fileId: string; name: string; size: number }): void
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)
let dragEnterDepth = 0
const uploadingFiles = ref<UploadingFile[]>([])
const uploadedFiles = ref<UploadedFile[]>([])
const failedFiles = ref<FailedFile[]>([])
const cancelledUploads = new Set<string>()

// 动态配置
const maxFileSize = ref(10 * 1024 * 1024) // 默认 10MB
const maxChunkSize = ref(2 * 1024 * 1024) // 默认 2MB

function handlePaste(e: ClipboardEvent) {
  if (!props.visible) return
  const files = e.clipboardData?.files
  if (files && files.length > 0) {
    e.preventDefault()
    processFiles(Array.from(files))
  }
}

onMounted(async () => {
  document.addEventListener('paste', handlePaste)
  const config = await getPublicConfig()
  maxFileSize.value = config.max_upload_file_size
  maxChunkSize.value = config.max_chunk_size
})

onUnmounted(() => {
  document.removeEventListener('paste', handlePaste)
})

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    processFiles(Array.from(input.files))
    input.value = ''
  }
}

function handleDragEnter() {
  dragEnterDepth += 1
  isDragOver.value = true
}

function handleDragOver() {
  // keep state on while dragging within the drop-zone
  if (!isDragOver.value) isDragOver.value = true
}

function handleDragLeave() {
  dragEnterDepth = Math.max(0, dragEnterDepth - 1)
  if (dragEnterDepth === 0) isDragOver.value = false
}

function handleDrop(e: DragEvent) {
  dragEnterDepth = 0
  isDragOver.value = false
  if (e.dataTransfer?.files) {
    processFiles(Array.from(e.dataTransfer.files))
  }
}

async function processFiles(files: File[]) {
  const maxSize = maxFileSize.value
  const maxSizeMB = (maxSize / 1024 / 1024).toFixed(0)
  const validFiles = files.filter(file => {
    if (file.size > maxSize) {
      snackbar({ message: `文件 ${file.name} 超过 ${maxSizeMB}MB 限制`, closeable: true })
      return false
    }
    return true
  })

  if (validFiles.length === 0) return

  // 确保 Paste 已创建
  if (!props.pasteId || !props.encryptionKey) {
    const ready = await props.onEnsurePaste()
    if (!ready) {
      snackbar({ message: '创建 Paste 失败', closeable: true })
      return
    }
  }

  for (const file of validFiles) {
    startUpload(file)
  }
}

async function startUpload(file: File) {
  const id = crypto.randomUUID()
  const abortController = new AbortController()
  const uploadingFile: UploadingFile = {
    id,
    name: file.name,
    size: file.size,
    progress: 0,
    speed: 0,
    file,
    abortController
  }
  let lastTime = Date.now()
  let lastLoaded = 0
  uploadingFiles.value.push(uploadingFile)

  try {
    if (!props.encryptionKey) {
      throw new Error('加密密钥未就绪')
    }

    const throwIfAborted = () => {
      if (abortController.signal.aborted) {
        throw new DOMException('Upload cancelled', 'AbortError')
      }
    }

    throwIfAborted()

    // 加密文件名
    const encryptedNameBytes = await encryptWithKey(file.name, props.encryptionKey)
    const encryptedName = bytesToStr(encryptedNameBytes)

    // 初始化上传
    const initRes = await initFileUpload(
      props.pasteId,
      props.adminKey,
      {
        encryption_mode: 'client',
        file_name: encryptedName,
        mime_type: file.type || 'application/octet-stream',
        file_size: file.size,
        requested_chunk_size: maxChunkSize.value
      },
      undefined,
      abortController.signal
    )

    uploadingFile.uploadId = initRes.upload_id
    const { upload_id, chunk_size, total_chunks } = initRes

    // 分片上传
    for (let i = 0; i < total_chunks; i++) {
      throwIfAborted()
      const start = i * chunk_size
      const end = Math.min(start + chunk_size, file.size)
      const chunkData = new Uint8Array(await file.slice(start, end).arrayBuffer())

      // 加密分片
      const encryptedChunk = await encryptFileChunk(chunkData, props.encryptionKey, {
        pasteId: props.pasteId,
        uploadId: upload_id,
        fileId: upload_id,
        chunkIndex: i,
        totalChunks: total_chunks
      })

      // 上传分片
      throwIfAborted()
      await uploadFileChunk(props.pasteId, props.adminKey, upload_id, i, encryptedChunk, (loaded, total) => {
        const file = uploadingFiles.value.find(f => f.id === id)
        if (file) {
          const chunkProgress = total > 0 ? loaded / total : 0
          file.progress = Math.round((i + chunkProgress) / total_chunks * 100)
          // 计算速度
          const now = Date.now()
          const totalLoaded = start + loaded
          const timeDiff = (now - lastTime) / 1000
          if (timeDiff > 0.1) {
            file.speed = (totalLoaded - lastLoaded) / timeDiff
            lastTime = now
            lastLoaded = totalLoaded
          }
        }
      }, abortController.signal)
    }

    // 完成上传
    throwIfAborted()
    const completeRes = await completeFileUpload(props.pasteId, props.adminKey, upload_id, {}, undefined, abortController.signal)

    // 移动到已上传列表
    uploadingFiles.value = uploadingFiles.value.filter(f => f.id !== id)
    uploadedFiles.value.push({
      id,
      fileId: completeRes.file_id,
      name: file.name,
      size: file.size
    })

    snackbar({ message: `${file.name} 上传成功` })
  } catch (error) {
    const isCancelled =
      cancelledUploads.has(id) ||
      abortController.signal.aborted ||
      (typeof error === 'object' &&
        error !== null &&
        ('code' in error && (error as any).code === 'ERR_CANCELED')) ||
      (typeof error === 'object' &&
        error !== null &&
        ('name' in error && ((error as any).name === 'CanceledError' || (error as any).name === 'AbortError')))

    if (isCancelled) {
      uploadingFiles.value = uploadingFiles.value.filter(f => f.id !== id)
      if (!cancelledUploads.has(id) && uploadingFile.uploadId) {
        try {
          await abortFileUpload(props.pasteId, props.adminKey, uploadingFile.uploadId)
        } catch (e) {
          console.error('Abort failed:', e)
        }
      }
      cancelledUploads.delete(id)
      return
    }

    console.error('Upload failed:', error)
    uploadingFiles.value = uploadingFiles.value.filter(f => f.id !== id)
    failedFiles.value.push({
      id,
      name: file.name,
      size: file.size,
      error: error instanceof Error ? error.message : '上传失败',
      file
    })
  }
}

async function cancelUpload(id: string) {
  const file = uploadingFiles.value.find(f => f.id === id)
  cancelledUploads.add(id)
  file?.abortController?.abort()
  if (file?.uploadId) {
    try {
      await abortFileUpload(props.pasteId, props.adminKey, file.uploadId)
    } catch (e) {
      console.error('Abort failed:', e)
    }
  }
  uploadingFiles.value = uploadingFiles.value.filter(f => f.id !== id)
}

function insertFile(file: UploadedFile) {
  emit('insert-file', {
    fileId: file.fileId,
    name: file.name,
    size: file.size
  })
}

async function removeFile(id: string) {
  const file = uploadedFiles.value.find(f => f.id === id)
  if (file) {
    try {
      await deleteFile(props.pasteId, props.adminKey, file.fileId)
      uploadedFiles.value = uploadedFiles.value.filter(f => f.id !== id)
    } catch (e) {
      console.error('Delete file failed:', e)
      snackbar({ message: '删除文件失败', closeable: true })
    }
  }
}

function retryUpload(file: FailedFile) {
  failedFiles.value = failedFiles.value.filter(f => f.id !== file.id)
  startUpload(file.file)
}

function dismissFailed(id: string) {
  failedFiles.value = failedFiles.value.filter(f => f.id !== id)
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec < 1024) return bytesPerSec.toFixed(0) + ' B/s'
  if (bytesPerSec < 1024 * 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s'
  return (bytesPerSec / (1024 * 1024)).toFixed(1) + ' MB/s'
}

function truncateFileName(name: string, maxLength: number = 20): string {
  if (name.length <= maxLength) return name
  const lastDot = name.lastIndexOf('.')
  const ext = lastDot > 0 ? name.slice(lastDot) : ''
  const baseName = lastDot > 0 ? name.slice(0, lastDot) : name
  const keepLength = maxLength - ext.length - 3 // 3 for '...'
  if (keepLength <= 0) return name.slice(0, maxLength - 3) + '...'
  return baseName.slice(0, keepLength) + '...' + ext
}
</script>

<style scoped>
.file-uploader {
  background: rgb(var(--mdui-color-background));
  border-radius: 12px;
  padding: 0;
}

.drop-zone {
  border: 2px dashed rgb(var(--mdui-color-outline));
  border-radius: 8px;
  padding: 32px;
  margin-top: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: rgb(var(--mdui-color-primary));
  background: rgb(var(--mdui-color-primary-container));
  color: rgb(var(--mdui-color-on-primary-container));
}

.drop-zone.drag-over .drop-icon,
.drop-zone.drag-over p,
.drop-zone.drag-over .hint {
  color: rgb(var(--mdui-color-on-primary-container));
}

.drop-icon {
  font-size: 48px;
  color: rgb(var(--mdui-color-primary));
  margin-bottom: 8px;
}

.drop-zone p {
  margin: 4px 0;
  color: rgb(var(--mdui-color-on-surface));
}

.drop-zone .hint {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.file-list {
  margin-top: 16px;
}

.file-list:last-child {
  padding-bottom: 16px;
}

.drop-zone:last-child {
  margin-bottom: 16px;
}

.list-header {
  font-size: 12px;
  font-weight: 500;
  color: rgb(var(--mdui-color-on-surface-variant));
  margin-bottom: 8px;
  text-transform: uppercase;
}

.list-header.error {
  color: rgb(var(--mdui-color-error));
}

.list-scroll-container {
  max-height: 280px; /* 约5个列表项的高度 */
  overflow-y: auto;
}

.list-scroll-container mdui-list-item + mdui-list-item {
  margin-top: 2px;
}

.file-icon.success {
  color: rgb(var(--mdui-color-primary));
}

.file-icon.error {
  color: rgb(var(--mdui-color-error));
}

.file-size {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.file-status {
  font-size: 12px;
  color: rgb(var(--mdui-color-primary));
}

.file-error {
  font-size: 12px;
  color: rgb(var(--mdui-color-error));
}

/* 上传中的列表项 - 背景进度效果 */
.uploading-item {
  --upload-progress: 0%;
  position: relative;
  overflow: hidden;
  isolation: isolate;
}

.uploading-item::before {
  content: '';
  position: absolute;
  inset: 0;
  width: var(--upload-progress);
  background: rgb(var(--mdui-color-primary-container));
  transition: width 0.3s ease-out;
  z-index: -1;
  pointer-events: none;
}

/* 上传失败的列表项 */
.failed-item {
  background: rgba(var(--mdui-color-error-container), 1);
}

.action-buttons {
  display: flex;
  gap: 4px;
}

/* 展开/收起动画 */
.file-uploader-wrapper {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.3s var(--mdui-motion-easing-standard);
}

.file-uploader-wrapper.expanded {
  grid-template-rows: 1fr;
  margin-bottom: 16px;
}

.file-uploader-wrapper > .file-uploader {
  overflow: hidden;
  min-height: 0;
  pointer-events: none;
}

.file-uploader-wrapper.expanded > .file-uploader {
  pointer-events: auto;
}
</style>
