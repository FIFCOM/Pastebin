<template>
  <div class="file-uploader-wrapper" :class="{ expanded: visible }">
    <div class="file-uploader">
      <FileUploaderDropZone
        :max-file-size="maxFileSize"
        :show-capacity="showCapacity"
        :capacity-text="capacityText"
        :show-capacity-bar="showCapacityBar"
        :capacity-used-bytes="capacityUsedBytes"
        :capacity-max-bytes="capacityMaxBytes"
        :bottom-gap="!hasAnyList"
        @files="handleDropZoneFiles"
      />
      <FileUploaderLists
        :uploading-files="uploadingFiles"
        :uploaded-files="uploadedFiles"
        :failed-files="failedFiles"
        @cancel-upload="cancelUpload"
        @insert-file="insertFile"
        @remove-file="removeFile"
        @retry-upload="retryUpload"
        @dismiss-failed="dismissFailed"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue'
import FileUploaderDropZone from './FileUploaderDropZone.vue'
import FileUploaderLists from './FileUploaderLists.vue'
import type { UploadedFile } from './types'
import { useFileUploader } from '../../composables/useFileUploader'

const props = defineProps<{
  visible: boolean
  pasteId: string
  adminKey: string
  encryptionKey: Uint8Array | null
  maxTotalUploadSize: number | null
  remainingUploadSize: number | null
  onEnsurePaste: () => Promise<boolean>
}>()

const emit = defineEmits<{
  (e: 'insert-file', file: { fileId: string; name: string; size: number }): void
}>()

const { pasteId, adminKey, encryptionKey, maxTotalUploadSize, remainingUploadSize } = toRefs(props)
const {
  uploadingFiles,
  uploadedFiles,
  failedFiles,
  maxFileSize,
  capacityMaxBytes,
  capacityUsedBytes,
  showCapacity,
  showCapacityBar,
  capacityText,
  processFiles,
  cancelUpload,
  removeFile,
  retryUpload,
  dismissFailed
} = useFileUploader({
  pasteId,
  adminKey,
  encryptionKey,
  maxTotalUploadSize,
  remainingUploadSize,
  onEnsurePaste: props.onEnsurePaste,
  onAutoInsert: (file) => emit('insert-file', file)
})

const hasAnyList = computed(
  () =>
    uploadingFiles.value.length > 0 || uploadedFiles.value.length > 0 || failedFiles.value.length > 0
)

const isUploading = computed(() => uploadingFiles.value.length > 0)

function handleDropZoneFiles(files: File[], meta: { source: 'select' | 'drop' }) {
  processFiles(files, { source: meta.source })
}

function insertFile(file: UploadedFile) {
  emit('insert-file', { fileId: file.fileId, name: file.name, size: file.size })
}

defineExpose({
  processFiles,
  isUploading
})
</script>

<style scoped>
.file-uploader {
  background: rgb(var(--mdui-color-background));
  border-radius: 12px;
  padding: 0;
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
