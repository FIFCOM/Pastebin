<template>
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
          <span slot="description" class="file-status">
            {{ file.state === 'queued' ? '排队中' : `${file.progress}% · ${formatSpeed(file.speed)}` }}
          </span>
          <mdui-button-icon
            slot="end-icon"
            icon="close"
            @click="emit('cancel-upload', file.id)"
          ></mdui-button-icon>
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
            <mdui-button-icon icon="add_link" @click="emit('insert-file', file)"></mdui-button-icon>
            <mdui-button-icon icon="delete" @click="emit('remove-file', file.id)"></mdui-button-icon>
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
            <mdui-button-icon icon="refresh" @click="emit('retry-upload', file)"></mdui-button-icon>
            <mdui-button-icon icon="close" @click="emit('dismiss-failed', file.id)"></mdui-button-icon>
          </div>
        </mdui-list-item>
      </mdui-list>
    </div>
  </div>
</template>

<script setup lang="ts">
import 'mdui/components/button-icon.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/icon.js'
import 'mdui/components/list.js'
import 'mdui/components/list-item.js'
import type { FailedFile, UploadedFile, UploadingFile } from './types'

defineProps<{
  uploadingFiles: UploadingFile[]
  uploadedFiles: UploadedFile[]
  failedFiles: FailedFile[]
}>()

const emit = defineEmits<{
  (e: 'cancel-upload', id: string): void
  (e: 'insert-file', file: UploadedFile): void
  (e: 'remove-file', id: string): void
  (e: 'retry-upload', file: FailedFile): void
  (e: 'dismiss-failed', id: string): void
}>()

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
.file-list {
  margin-top: 16px;
}

.file-list:last-child {
  padding-bottom: 16px;
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
  background: rgb(var(--mdui-color-secondary-container));
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
</style>

