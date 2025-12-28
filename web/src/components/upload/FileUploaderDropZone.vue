<template>
  <div
    class="drop-zone"
    :class="{ 'drag-over': isDragOver, 'with-bottom-gap': bottomGap }"
    @dragenter.prevent="handleDragEnter"
    @dragover.prevent="handleDragOver"
    @dragleave.prevent="handleDragLeave"
    @drop.prevent="handleDrop"
    @click="triggerFileInput"
  >
    <mdui-icon name="cloud_upload" class="drop-icon"></mdui-icon>
    <p>拖拽/粘贴文件到此处，或点击选择文件</p>
    <p class="hint">单个文件最大 {{ maxFileSizeMB }}MB</p>
    <div v-show="showCapacity" class="capacity">
      <div class="capacity-row">
        <span class="capacity-label">容量</span>
        <span class="capacity-value">{{ capacityText }}</span>
      </div>
      <mdui-linear-progress
        v-if="showCapacityBar"
        class="capacity-bar"
        :value="capacityUsedBytes!"
        :max="capacityMaxBytes!"
      ></mdui-linear-progress>
    </div>
    <input ref="fileInputRef" type="file" multiple hidden @change="handleFileSelect" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'

const props = defineProps<{
  maxFileSize: number
  showCapacity: boolean
  capacityText: string
  showCapacityBar: boolean
  capacityUsedBytes: number | null
  capacityMaxBytes: number | null
  bottomGap?: boolean
}>()

const emit = defineEmits<{
  (e: 'files', files: File[], meta: { source: 'select' | 'drop' }): void
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)
let dragEnterDepth = 0

const maxFileSizeMB = computed(() => Math.round(props.maxFileSize / 1024 / 1024))
const bottomGap = computed(() => props.bottomGap ?? false)

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    emit('files', Array.from(input.files), { source: 'select' })
    input.value = ''
  }
}

function handleDragEnter() {
  dragEnterDepth += 1
  isDragOver.value = true
}

function handleDragOver() {
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
    emit('files', Array.from(e.dataTransfer.files), { source: 'drop' })
  }
}
</script>

<style scoped>
.capacity {
  margin: 18px auto 0 auto;
  width: min(520px, 80%);
  pointer-events: none;
}

.capacity-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.capacity-label {
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.capacity-value {
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface));
}

.capacity-bar {
  width: 100%;
}

.drop-zone {
  border: 2px dashed rgb(var(--mdui-color-outline));
  border-radius: 8px;
  padding: 32px;
  margin-top: 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s, color 0.2s;
}

.drop-zone.with-bottom-gap {
  margin-bottom: 16px;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: rgb(var(--mdui-color-primary));
  background: rgb(var(--mdui-color-secondary-container));
  color: rgb(var(--mdui-color-on-secondary-container));
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
</style>
