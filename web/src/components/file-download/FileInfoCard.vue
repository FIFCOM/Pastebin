<template>
  <mdui-card class="file-info-card">
    <div class="file-header">
      <div class="file-header-main">
        <div class="file-title" :title="displayName">{{ displayName }}</div>
        <div v-if="encryptionLabel" class="file-subtitle" title="加密状态">
          <mdui-icon
            :name="encryptionMode === 'client' ? 'enhanced_encryption' : 'lock'"
            class="file-subtitle-icon"
          ></mdui-icon>
          <span>{{ encryptionLabel }}</span>
        </div>
      </div>

      <div class="file-header-actions">
        <mdui-button-icon
          :icon="shareUrlCopied ? 'check' : 'content_copy'"
          :disabled="!shareUrl"
          :title="shareUrlCopied ? '已复制' : '复制分享链接'"
          @click="emit('copyShareUrl')"
        ></mdui-button-icon>
      </div>
    </div>

    <div class="file-meta">
      <div class="file-meta-row">
        <span class="label label-with-icon">
          <mdui-icon-storage></mdui-icon-storage>
          大小
        </span>
        <span class="value">{{ plainSizeText }}</span>
      </div>

      <div v-if="hasCreatedAt" class="file-meta-row">
        <span class="label label-with-icon">
          <mdui-icon-create></mdui-icon-create>
          上传时间
        </span>
        <span class="value">{{ createdAtText }}</span>
      </div>

      <div v-if="hasPasteInfo" class="file-meta-row">
        <span class="label label-with-icon">
          <mdui-icon-auto-delete></mdui-icon-auto-delete>
          过期时间
        </span>
        <span class="value">{{ pasteExpireText }}</span>
      </div>
    </div>

    <div v-if="showProgress" class="progress-section">
      <mdui-linear-progress
        class="download-progress"
        :class="{ 'is-error': downloadState === 'error' }"
        :value="progressValue"
        :max="1"
      ></mdui-linear-progress>
      <div class="progress-text">
        {{ progressText }}
      </div>
    </div>

    <div class="actions">
      <mdui-button
        full-width
        :disabled="isDownloading"
        :loading="isDownloading"
        @click="emit('download')"
      >
        <mdui-icon slot="icon" name="download"></mdui-icon>
        {{ downloadButtonText }}
      </mdui-button>
    </div>
  </mdui-card>
</template>

<script setup lang="ts">
import type { DownloadState } from '@/components/file-download/types'
import { computed } from 'vue'

import 'mdui/components/card.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import '@mdui/icons/auto-delete.js'
import '@mdui/icons/create.js'
import '@mdui/icons/storage.js'

const props = defineProps<{
  displayName: string
  encryptionLabel: string
  encryptionMode: '' | 'client' | 'server'
  shareUrl: string
  shareUrlCopied: boolean
  plainSizeText: string
  createdAtText: string
  hasCreatedAt: boolean
  hasPasteInfo: boolean
  pasteExpireText: string
  showProgress: boolean
  progressValue: number
  progressText: string
  isDownloading: boolean
  downloadState: DownloadState
}>()

const emit = defineEmits<{
  copyShareUrl: []
  download: []
}>()

const downloadLabelByState: Partial<Record<DownloadState, string>> = {
  done: '重新下载',
}

const downloadButtonText = computed(() => {
  if (props.isDownloading) {
    return '下载中'
  }
  return downloadLabelByState[props.downloadState] ?? '下载'
})
</script>

<style scoped>
.file-info-card {
  width: 360px;
  padding: 16px;
  margin-left: auto;
  align-self: flex-start;
}

.file-header {
  margin-bottom: 14px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.file-header-main {
  min-width: 0;
  flex: 1 1 0;
}

.file-header-actions {
  flex: 0 0 auto;
}

.file-title {
  font-size: 18px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface));
  min-width: 0;
  white-space: normal;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-clamp: 2;
  -webkit-line-clamp: 2;
}

.file-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: rgb(var(--mdui-color-outline));
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.file-subtitle-icon {
  font-size: 15px;
}

.file-meta {
  display: grid;
  gap: 8px;
  margin-bottom: 18px;
}

.file-meta-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.file-meta-row .label {
  color: rgb(var(--mdui-color-on-surface));
}

.file-meta-row .label-with-icon {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.file-meta-row .label-with-icon :is(mdui-icon-storage, mdui-icon-create, mdui-icon-auto-delete) {
  font-size: 15px;
}

.file-meta-row .value {
  color: rgb(var(--mdui-color-on-surface));
  word-break: break-all;
}

.progress-section {
  margin-top: 10px;
  margin-bottom: 10px;
}

.progress-text {
  margin-top: 6px;
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface));
  text-align: right;
}

.download-progress {
  --mdui-motion-duration-long2: 0ms;
}

.download-progress.is-error {
  background-color: rgb(var(--mdui-color-error-container));
}

.download-progress.is-error::part(indicator) {
  background-color: rgb(var(--mdui-color-error));
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 14px;
  width: 100%;
}

.actions mdui-button {
  width: 100%;
}

@media (max-width: 900px) {
  .file-info-card {
    width: 100%;
    order: -1;
  }
}
</style>
