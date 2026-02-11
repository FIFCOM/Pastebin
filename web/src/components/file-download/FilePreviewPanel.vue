<template>
  <div class="file-preview">
    <div v-if="isVideo" class="preview-section">
      <div v-if="videoSrc" class="video-container">
        <video class="video-player" controls preload="metadata" :src="videoSrc"></video>
      </div>
      <PreviewPlaceholder v-else />
    </div>

    <div v-else-if="isImage" class="preview-section">
      <div v-if="imageSrc" class="image-container">
        <img
          class="image-preview"
          :src="imageSrc"
          :alt="displayName"
          title="点击放大"
          @click="emit('imagePreview')"
        />
      </div>
      <PreviewPlaceholder v-else />
    </div>

    <div v-else-if="isAudio" class="preview-section">
      <div v-if="audioSrc" class="audio-container">
        <audio class="audio-player" controls preload="metadata" :src="audioSrc"></audio>
      </div>
      <PreviewPlaceholder v-else />
    </div>

    <div v-else-if="isText" class="preview-section">
      <div class="text-preview-container">
        <div class="text-preview-header">
          <div class="text-preview-title">文本预览</div>
          <div class="text-preview-subtitle">前 {{ textPreviewLabel }}</div>
        </div>

        <div v-if="textPreviewLoading" class="text-preview-loading">
          <mdui-circular-progress></mdui-circular-progress>
          <div class="hint">正在解密预览内容…</div>
        </div>

        <PreviewPlaceholder
          v-else-if="textPreviewError"
          :message="textPreviewError"
          hint="你仍然可以直接下载该文件。"
        />

        <pre v-else class="text-preview"><code class="mdui-prose">{{ textPreview }}</code></pre>

        <div v-if="textPreviewTruncated" class="text-preview-hint">
          仅展示前 {{ textPreviewLabel }}，完整内容请下载。
        </div>
      </div>
    </div>

    <div v-else class="file-icon-section">
      <mdui-icon :name="fileTypeIcon" class="file-icon"></mdui-icon>
      <div class="file-icon-name">{{ displayName }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import PreviewPlaceholder from '@/components/common/PreviewPlaceholder.vue'

import 'mdui/components/circular-progress.js'
import 'mdui/components/icon.js'

defineProps<{
  isVideo: boolean
  isImage: boolean
  isAudio: boolean
  isText: boolean
  videoSrc: string
  imageSrc: string
  audioSrc: string
  displayName: string
  fileTypeIcon: string
  textPreviewLabel: string
  textPreviewLoading: boolean
  textPreviewError: string
  textPreview: string
  textPreviewTruncated: boolean
}>()

const emit = defineEmits<{
  imagePreview: []
}>()
</script>

<style scoped>
.file-preview {
  flex: 1 1 0;
  min-width: 0;
}

.preview-section {
  margin-bottom: 16px;
}

.video-container {
  border-radius: 10px;
  overflow: hidden;
  background: #000;
}

.video-player {
  width: 100%;
  max-height: min(60vh, 560px);
  display: block;
}

.image-container {
  border-radius: 10px;
  overflow: hidden;
  background-color: rgb(var(--mdui-color-surface));
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
}

.image-preview {
  max-width: 100%;
  max-height: min(60vh, 560px);
  height: auto;
  display: block;
  border-radius: 8px;
  object-fit: contain;
  cursor: zoom-in;
}

.audio-container {
  border-radius: 10px;
  background-color: rgb(var(--mdui-color-surface));
  padding: 12px;
}

.audio-player {
  width: 100%;
}

.text-preview-container {
  border-radius: 10px;
  background-color: rgb(var(--mdui-color-surface));
  padding: 12px;
}

.text-preview-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.text-preview-title {
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface));
}

.text-preview-subtitle {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
  white-space: nowrap;
}

.text-preview-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  color: rgb(var(--mdui-color-on-surface-variant));
  font-size: 13px;
}

.text-preview {
  margin: 0;
  padding: 12px;
  border-radius: 8px;
  background-color: rgb(var(--mdui-color-surface-container));
  white-space: pre-wrap;
  word-break: break-word;
  max-height: min(60vh, 560px);
  overflow: auto;
}

.text-preview-hint {
  margin-top: 10px;
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.file-icon-section {
  border-radius: 12px;
  background-color: rgb(var(--mdui-color-secondary-container));
  padding: 32px 16px;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: rgb(var(--mdui-color-on-surface));
  gap: 12px;
}

.file-icon {
  font-size: 64px;
}

.file-icon-name {
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface));
  word-break: break-word;
}
</style>
