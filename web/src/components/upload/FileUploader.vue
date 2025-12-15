<template>
  <div v-if="visible" class="file-uploader">
    <!-- 拖拽上传区域 -->
    <div
      class="drop-zone"
      :class="{ 'drag-over': isDragOver }"
      @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <mdui-icon name="cloud_upload" class="drop-icon"></mdui-icon>
      <p>拖拽文件到此处，或点击选择文件</p>
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
      <div v-for="file in uploadingFiles" :key="file.id" class="file-item uploading">
        <mdui-icon name="description" class="file-icon"></mdui-icon>
        <div class="file-info">
          <span class="file-name">{{ file.name }}</span>
          <div class="progress-bar">
            <div class="progress" :style="{ width: file.progress + '%' }"></div>
          </div>
          <span class="file-status">{{ file.progress }}%</span>
        </div>
        <mdui-button-icon icon="close" @click="cancelUpload(file.id)"></mdui-button-icon>
      </div>
    </div>

    <!-- 已上传的文件列表 -->
    <div v-if="uploadedFiles.length > 0" class="file-list">
      <div class="list-header">已上传</div>
      <div v-for="file in uploadedFiles" :key="file.id" class="file-item uploaded">
        <mdui-icon name="check_circle" class="file-icon success"></mdui-icon>
        <div class="file-info">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatFileSize(file.size) }}</span>
        </div>
        <mdui-button-icon icon="add_link" @click="insertFile(file)"></mdui-button-icon>
        <mdui-button-icon icon="delete" @click="removeFile(file.id)"></mdui-button-icon>
      </div>
    </div>

    <!-- 上传失败的文件 -->
    <div v-if="failedFiles.length > 0" class="file-list">
      <div class="list-header error">上传失败</div>
      <div v-for="file in failedFiles" :key="file.id" class="file-item failed">
        <mdui-icon name="error" class="file-icon error"></mdui-icon>
        <div class="file-info">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-error">{{ file.error }}</span>
        </div>
        <mdui-button-icon icon="refresh" @click="retryUpload(file)"></mdui-button-icon>
        <mdui-button-icon icon="close" @click="dismissFailed(file.id)"></mdui-button-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import 'mdui/components/icon.js'
import 'mdui/components/button-icon.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import {
  initFileUpload,
  uploadFileChunk,
  completeFileUpload,
  abortFileUpload
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
const uploadingFiles = ref<UploadingFile[]>([])
const uploadedFiles = ref<UploadedFile[]>([])
const failedFiles = ref<FailedFile[]>([])

// 动态配置
const maxFileSize = ref(10 * 1024 * 1024) // 默认 10MB
const maxChunkSize = ref(2 * 1024 * 1024) // 默认 2MB
const configLoaded = ref(false)

onMounted(async () => {
  const config = await getPublicConfig()
  maxFileSize.value = config.max_upload_file_size
  maxChunkSize.value = config.max_chunk_size
  configLoaded.value = true
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

function handleDrop(e: DragEvent) {
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
  const uploadingFile: UploadingFile = {
    id,
    name: file.name,
    size: file.size,
    progress: 0,
    file
  }
  uploadingFiles.value.push(uploadingFile)

  try {
    if (!props.encryptionKey) {
      throw new Error('加密密钥未就绪')
    }

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
      }
    )

    uploadingFile.uploadId = initRes.upload_id
    const { upload_id, chunk_size, total_chunks } = initRes

    // 分片上传
    for (let i = 0; i < total_chunks; i++) {
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
      await uploadFileChunk(props.pasteId, props.adminKey, upload_id, i, encryptedChunk)

      // 更新进度
      const idx = uploadingFiles.value.findIndex(f => f.id === id)
      if (idx !== -1) {
        uploadingFiles.value[idx].progress = Math.round(((i + 1) / total_chunks) * 100)
      }
    }

    // 完成上传
    const completeRes = await completeFileUpload(props.pasteId, props.adminKey, upload_id)

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

function removeFile(id: string) {
  uploadedFiles.value = uploadedFiles.value.filter(f => f.id !== id)
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
</script>

<style scoped>
.file-uploader {
  background: var(--mdui-color-surface-container);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.drop-zone {
  border: 2px dashed var(--mdui-color-outline);
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: var(--mdui-color-primary);
  background: var(--mdui-color-primary-container);
}

.drop-icon {
  font-size: 48px;
  color: var(--mdui-color-primary);
  margin-bottom: 8px;
}

.drop-zone p {
  margin: 4px 0;
  color: var(--mdui-color-on-surface);
}

.drop-zone .hint {
  font-size: 12px;
  color: var(--mdui-color-on-surface-variant);
}

.file-list {
  margin-top: 16px;
}

.list-header {
  font-size: 12px;
  font-weight: 500;
  color: var(--mdui-color-on-surface-variant);
  margin-bottom: 8px;
  text-transform: uppercase;
}

.list-header.error {
  color: var(--mdui-color-error);
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--mdui-color-surface);
  border-radius: 8px;
  margin-bottom: 8px;
}

.file-icon {
  font-size: 24px;
  color: var(--mdui-color-on-surface-variant);
}

.file-icon.success {
  color: var(--mdui-color-primary);
}

.file-icon.error {
  color: var(--mdui-color-error);
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  display: block;
  font-size: 14px;
  color: var(--mdui-color-on-surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 12px;
  color: var(--mdui-color-on-surface-variant);
}

.file-status {
  font-size: 12px;
  color: var(--mdui-color-primary);
}

.file-error {
  font-size: 12px;
  color: var(--mdui-color-error);
}

.progress-bar {
  height: 4px;
  background: var(--mdui-color-surface-variant);
  border-radius: 2px;
  margin-top: 4px;
  overflow: hidden;
}

.progress {
  height: 100%;
  background: var(--mdui-color-primary);
  transition: width 0.2s;
}
</style>
