<template>
  <mdui-dialog ref="dialogRef" headline="附件列表">
    <div class="dialog-content">
      <div v-if="isResolving" class="loading-row">
        <mdui-circular-progress></mdui-circular-progress>
        <span>正在解析文件名...</span>
      </div>

      <div v-else-if="resolvedFiles.length === 0" class="empty-state">
        当前 Paste 没有上传文件
      </div>

      <div v-else class="file-list-scroll">
        <div class="file-list">
          <mdui-card
            v-for="file in resolvedFiles"
            :key="file.id"
            variant="filled"
            class="file-card"
            role="button"
            tabindex="0"
            @click="openFileDownload(file.id)"
            @keydown.enter.prevent="openFileDownload(file.id)"
            @keydown.space.prevent="openFileDownload(file.id)"
          >
            <mdui-icon :name="file.icon" class="file-icon"></mdui-icon>
            <div class="file-main">
              <div class="file-name" :title="file.name">{{ file.name }}</div>
              <div class="file-size">{{ file.sizeText }}</div>
            </div>
          </mdui-card>
        </div>
      </div>
    </div>

    <mdui-button slot="action" variant="text" @click="close">
      关闭
    </mdui-button>
  </mdui-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { PasteFile } from '@/services/paste'
import { decryptWithKey, keyToUrlSafeStr, strToBytes } from '@/utils/crypto'
import { buildMbDownloadPageHref } from '@/utils/mbFile'
import { fileTypeToIconName } from '@/utils/fileTypeIcon'
import { humanSize } from '@/utils/format'

import 'mdui/components/button.js'
import 'mdui/components/card.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/dialog.js'
import 'mdui/components/icon.js'

type PasteFileLike = PasteFile & {
  name?: string | null
  mime_type?: string | null
}

type ResolvedFile = {
  id: string
  name: string
  sizeText: string
  icon: string
}

const props = defineProps<{
  files: PasteFileLike[]
  pasteId: string
  encryptionKey: Uint8Array | null
  encryptionKeyHash?: string
}>()

const dialogRef = ref<any>(null)
const isResolving = ref(false)
const resolvedFiles = ref<ResolvedFile[]>([])
let resolveTicket = 0

function open() {
  if (dialogRef.value) dialogRef.value.open = true
}

function close() {
  if (dialogRef.value) dialogRef.value.open = false
}

function normalizeHash(raw: string): string {
  const v = (raw || '').trim()
  if (!v) return ''
  return v.startsWith('#') ? v : `#${v}`
}

const downloadHash = computed(() => {
  const provided = normalizeHash(props.encryptionKeyHash || '')
  if (provided) return provided
  if (props.encryptionKey) return `#${keyToUrlSafeStr(props.encryptionKey)}`
  return ''
})

function openFileDownload(fileId: string) {
  if (!props.pasteId || !fileId) return
  const href = buildMbDownloadPageHref(props.pasteId, fileId, {
    encryptionKeyHash: downloadHash.value
  })
  const win = window.open(href, '_blank', 'noopener,noreferrer')
  if (!win) {
    window.location.href = href
  }
}

async function decryptFileName(file: PasteFileLike): Promise<string> {
  const plainName = (file.name || '').trim()
  if (plainName) return plainName

  const fallback = `mb_encrypted_${file.id}`
  if (!props.encryptionKey || !file.encrypted_name) return fallback

  try {
    const nameBytesEncrypted = strToBytes(file.encrypted_name)
    const nameBytes = await decryptWithKey(nameBytesEncrypted, props.encryptionKey)
    const name = new TextDecoder().decode(nameBytes).trim()
    return name || fallback
  } catch {
    return fallback
  }
}

function fileDisplaySize(file: PasteFileLike): number {
  const plain = Number(file.plain_size)
  if (Number.isFinite(plain) && plain >= 0) return plain

  const encrypted = Number(file.size)
  if (Number.isFinite(encrypted) && encrypted >= 0) return encrypted

  return 0
}

async function rebuildResolvedFiles() {
  const ticket = ++resolveTicket
  const files = Array.isArray(props.files) ? props.files : []
  if (files.length === 0) {
    resolvedFiles.value = []
    isResolving.value = false
    return
  }

  isResolving.value = true
  const next: ResolvedFile[] = []

  for (const file of files) {
    const name = await decryptFileName(file)
    const size = fileDisplaySize(file)
    const mime = String(file.mime_type || 'application/octet-stream')
    next.push({
      id: file.id,
      name,
      sizeText: humanSize(size),
      icon: fileTypeToIconName(mime, name)
    })
  }

  if (ticket !== resolveTicket) return
  resolvedFiles.value = next
  isResolving.value = false
}

watch(
  () => [props.files, props.encryptionKey],
  () => {
    void rebuildResolvedFiles()
  },
  { immediate: true }
)

defineExpose<{ open: () => void; close: () => void }>({
  open,
  close
})
</script>

<style scoped>
.dialog-content {
  padding: 10px 0;
}

.loading-row {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgb(var(--mdui-color-on-surface-variant));
  font-size: 14px;
  padding: 8px 2px;
}

.empty-state {
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface-variant));
  padding: 8px 2px;
}

.file-list {
  display: grid;
  gap: 10px;
}

.file-list-scroll {
  max-height: min(56vh, 520px);
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
}

.file-list-scroll::-webkit-scrollbar {
  width: 8px;
}

.file-list-scroll::-webkit-scrollbar-thumb {
  background: rgb(var(--mdui-color-outline-variant));
  border-radius: 8px;
}

.file-list-scroll::-webkit-scrollbar-track {
  background: rgb(var(--mdui-color-surface-container-low));
  border-radius: 8px;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.file-card:hover {
  background-color: rgb(var(--mdui-color-surface-container-high));
}

.file-card:focus-visible {
  outline: 2px solid rgb(var(--mdui-color-primary));
  outline-offset: 2px;
}

.file-icon {
  font-size: 38px;
  color: rgb(var(--mdui-color-primary));
  flex: 0 0 auto;
}

.file-main {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 12px;
  color: rgb(var(--mdui-color-on-surface-variant));
}
</style>
