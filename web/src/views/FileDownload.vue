<template>
  <div class="file-download-view">
    <div v-if="isLoading" class="loading-indicator">
      <mdui-circular-progress></mdui-circular-progress>
    </div>

    <div v-else-if="error" class="error-box">
      <mdui-icon name="error"></mdui-icon>
      <div class="error-text">{{ error }}</div>
    </div>

    <div v-else class="file-card">
      <div class="file-header">
        <div class="file-title">{{ displayName }}</div>
        <div class="file-subtitle">{{ meta?.mime_type || 'application/octet-stream' }}</div>
      </div>

      <div class="file-meta">
        <div class="file-meta-row">
          <span class="label">Paste</span>
          <span class="value">{{ pasteId }}</span>
        </div>
        <div class="file-meta-row">
          <span class="label">File</span>
          <span class="value">{{ fileId }}</span>
        </div>
        <div class="file-meta-row">
          <span class="label">大小</span>
          <span class="value">{{ humanSize(plainSize || 0) }}</span>
        </div>
      </div>

      <div v-if="isVideo" class="video-section">
        <div class="video-title">视频预览</div>
        <div v-if="videoPlainSrc" class="video-container">
          <video class="video-player" controls preload="metadata" :src="videoPlainSrc"></video>
        </div>
        <div v-else class="video-placeholder">
          <div>预览需要 Service Worker 流式解密（支持拖拽进度条）。</div>
          <div class="hint">若无法播放：请确认浏览器支持 SW，并刷新页面。</div>
        </div>
      </div>

      <div v-if="isBusy" class="progress-section">
        <mdui-linear-progress :value="progressDone" :max="progressTotal"></mdui-linear-progress>
        <div class="progress-text">
          {{ humanSize(progressDone) }} / {{ humanSize(progressTotal) }}
        </div>
      </div>

      <div class="actions">
        <mdui-button variant="tonal" @click="goBackToPaste">返回 Paste</mdui-button>
        <mdui-button :disabled="isBusy" @click="handleDownload">下载</mdui-button>
      </div>
    </div>

    <!-- Access Key 输入对话框 -->
    <mdui-dialog
      ref="accessKeyDialog"
      headline="需要访问密钥"
      close-on-esc="false"
      close-on-overlay-click="false"
    >
      <mdui-icon slot="icon" name="lock" style="color: var(--mdui-color-primary);"></mdui-icon>
      <div class="dialog-content">
        <p class="dialog-description">此文件所属 Paste 受访问密钥保护，请输入密钥继续。</p>

        <div class="config-section">
          <mdui-text-field
            v-model="accessKeyInput"
            label="访问密钥"
            placeholder="请输入访问密钥"
            type="password"
            variant="outlined"
            maxlength="72"
            counter
            @keydown.enter="handleAccessKeySubmit"
          ></mdui-text-field>
        </div>

        <div v-if="accessKeyError" class="warning-message">
          <mdui-icon name="error"></mdui-icon>
          <p>访问密钥验证失败，请重试。</p>
        </div>
      </div>

      <mdui-button
        slot="action"
        variant="tonal"
        @click="handleAccessKeySubmit"
        :disabled="!accessKeyInput.trim()"
      >
        确认
      </mdui-button>
    </mdui-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import { useTheme } from '@/composables/useTheme'
import { decryptWithKey, strToBytes, urlSafeStrToKey } from '@/utils/crypto'
import type { MbFileManifest } from '@/utils/mbFileDecrypt'
import { decryptChunkedFileStream, decryptChunkedFileToBlob } from '@/utils/mbFileDecrypt'
import { buildMbPlainFilePath, mbSwSetPasteContext } from '@/utils/mbSw'

import 'mdui/components/button.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/dialog.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
import 'mdui/components/text-field.js'

useTheme()

type FileMeta = {
  paste_id: string
  file_id: string
  encrypted_name: string
  mime_type: string
  encrypted_size: number
  plain_size?: number | null
  url: string
  manifest_url: string
}

const route = useRoute()
const router = useRouter()

const pasteId = computed(() => route.params.paste_id as string)
const fileId = computed(() => route.params.file_id as string)

const isLoading = ref(true)
const error = ref('')

const meta = ref<FileMeta | null>(null)
const manifest = ref<MbFileManifest | null>(null)

const encryptionKeyBytes = ref<Uint8Array | null>(null)
const decryptedName = ref<string>('')

const accessKey = ref<string | null>(null)
const accessKeyDialog = ref<any>(null)
const accessKeyInput = ref('')
const accessKeyError = ref(false)

const isBusy = ref(false)
const progressDone = ref(0)
const progressTotal = ref(0)

const videoPlainSrc = ref<string>('')

const plainSize = computed(() => manifest.value?.plain_size ?? meta.value?.plain_size ?? 0)
const displayName = computed(() => decryptedName.value || `mb_encrypted_${fileId.value}`)
const isVideo = computed(() => (meta.value?.mime_type || '').startsWith('video/'))

function humanSize(bytes: number): string {
  const n = Number(bytes)
  if (!Number.isFinite(n) || n < 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB'] as const
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  const unit = units[i] ?? 'B'
  const fixed = i === 0 ? v.toFixed(0) : v.toFixed(v >= 10 ? 1 : 2)
  return `${fixed} ${unit}`
}

function buildAccessKeyQuery(): string {
  const k = accessKey.value?.trim()
  if (!k) return ''
  return `?access_key=${encodeURIComponent(k)}`
}

function ensureEncryptionKey(): Uint8Array | null {
  if (encryptionKeyBytes.value) return encryptionKeyBytes.value

  const keyStr = window.location.hash.substring(1)
  if (!keyStr) {
    error.value = 'URL 中缺少加密密钥（hash 部分）。'
    return null
  }
  try {
    const key = urlSafeStrToKey(keyStr)
    encryptionKeyBytes.value = key
    return key
  } catch {
    error.value = '无效的加密密钥格式。'
    return null
  }
}

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url)
  if (!resp.ok) {
    const err = new Error(`HTTP ${resp.status}`)
    ;(err as any).status = resp.status
    throw err
  }
  return (await resp.json()) as T
}

async function loadMetaAndManifest(): Promise<void> {
  if (!pasteId.value || !fileId.value) {
    error.value = 'URL 缺少 paste_id 或 file_id。'
    return
  }
  const key = ensureEncryptionKey()
  if (!key) return

  // Try cached access key (same SPA session).
  if (!accessKey.value) {
    try {
      accessKey.value = sessionStorage.getItem(`mb_access_key:${pasteId.value}`)
    } catch {
      accessKey.value = null
    }
  }

  const metaUrl = `/api/pastes/${encodeURIComponent(pasteId.value)}/files/${encodeURIComponent(
    fileId.value
  )}/meta${buildAccessKeyQuery()}`
  const manifestUrl = `/api/pastes/${encodeURIComponent(pasteId.value)}/files/${encodeURIComponent(
    fileId.value
  )}/manifest${buildAccessKeyQuery()}`

  try {
    const [m, man] = await Promise.all([
      fetchJson<FileMeta>(metaUrl),
      fetchJson<MbFileManifest>(manifestUrl)
    ])

    meta.value = m
    manifest.value = man
    progressTotal.value = Number(man.plain_size) || 0

    // Decrypt file name on the client (server never sees the key).
    try {
      const nameBytesEncrypted = strToBytes(m.encrypted_name)
      const nameBytes = await decryptWithKey(nameBytesEncrypted, key)
      decryptedName.value = new TextDecoder().decode(nameBytes)
    } catch {
      decryptedName.value = ''
    }

    if (accessKey.value && accessKey.value.trim()) {
      try {
        sessionStorage.setItem(`mb_access_key:${pasteId.value}`, accessKey.value.trim())
      } catch {
        // ignore
      }
    }

    // Enable SW-based video preview (supports Range/seek).
    void enableVideoPreview()
  } catch (e: any) {
    const status = Number(e?.status)
    if (status === 403) {
      showAccessKeyDialog(false)
      return
    }
    if (status === 404) {
      error.value = '文件不存在或不可访问。'
      return
    }
    if (status === 410) {
      error.value = 'Paste 已过期或已达到最大查看次数。'
      return
    }
    error.value = `加载失败: ${e instanceof Error ? e.message : String(e)}`
    console.error('load meta/manifest failed:', e)
  }
}

async function enableVideoPreview(): Promise<void> {
  videoPlainSrc.value = ''
  if (!isVideo.value) return

  const key = ensureEncryptionKey()
  if (!key) return

  const ok = await mbSwSetPasteContext({
    pasteId: pasteId.value,
    encryptionKey: key,
    accessKey: accessKey.value
  })
  if (!ok) {
    snackbar({ message: '视频预览需要 Service Worker（请使用支持 SW 的浏览器）', closeable: true })
    return
  }

  videoPlainSrc.value = buildMbPlainFilePath(pasteId.value, fileId.value)
}

function showAccessKeyDialog(isRetry: boolean) {
  accessKeyError.value = isRetry
  accessKeyInput.value = ''
  if (accessKeyDialog.value) accessKeyDialog.value.open = true
}

async function handleAccessKeySubmit() {
  const k = accessKeyInput.value.trim()
  if (!k) {
    accessKeyError.value = true
    return
  }
  accessKey.value = k

  if (accessKeyDialog.value) accessKeyDialog.value.open = false

  isLoading.value = true
  error.value = ''
  await loadMetaAndManifest()

  if (error.value) {
    // Other errors are handled by the page error box.
    isLoading.value = false
    return
  }

  // If still no meta, it likely means 403 again.
  if (!meta.value || !manifest.value) {
    accessKeyError.value = true
    showAccessKeyDialog(true)
    isLoading.value = false
    return
  }

  isLoading.value = false
}

async function handleDownload() {
  if (isBusy.value) return
  const key = ensureEncryptionKey()
  if (!key) return
  if (!meta.value || !manifest.value) {
    snackbar({ message: '文件信息未就绪', closeable: true })
    return
  }

  const url = `${meta.value.url}${buildAccessKeyQuery()}`
  const plainTotal = Number(manifest.value.plain_size) || 0
  const encryptedTotal = (() => {
    const v = Number(meta.value?.encrypted_size)
    if (Number.isFinite(v) && v > 0) return v
    const overhead = Number(manifest.value?.chunk_overhead_bytes) || 0
    const chunks = Number(manifest.value?.total_chunks) || 0
    return plainTotal + overhead * chunks
  })()
  progressTotal.value = encryptedTotal
  progressDone.value = 0

  isBusy.value = true
  try {
    const picker = (window as any).showSaveFilePicker
    if (typeof picker === 'function') {
      const handle = await picker({
        suggestedName: displayName.value
      })
      const writable = await handle.createWritable()

      const resp = await fetch(url)
      if (!resp.ok || !resp.body) {
        throw new Error(`下载失败: HTTP ${resp.status}`)
      }

      for await (const plainChunk of decryptChunkedFileStream(
        resp.body,
        manifest.value,
        key,
        { pasteId: pasteId.value, fileId: fileId.value },
        {
          onEncryptedProgress: (done, totalBytes) => {
            progressDone.value = done
            progressTotal.value = totalBytes
          }
        }
      )) {
        await writable.write(plainChunk)
      }

      await writable.close()
      snackbar({ message: '已保存到本地' })
      return
    }

    // Fallback: decrypt to Blob then trigger download (memory-heavy).
    const MAX_BLOB_FALLBACK = 1024 * 1024 * 1024 // 1 GiB
    if (plainTotal > MAX_BLOB_FALLBACK) {
      throw new Error('文件过大，当前浏览器不支持无落盘 API 的流式下载（建议使用 Chromium）')
    }

    const resp = await fetch(url)
    if (!resp.ok || !resp.body) {
      throw new Error(`下载失败: HTTP ${resp.status}`)
    }

    const blob = await decryptChunkedFileToBlob(
      resp.body,
      manifest.value,
      key,
      { pasteId: pasteId.value, fileId: fileId.value },
      meta.value.mime_type || 'application/octet-stream',
      {
        onEncryptedProgress: (done, totalBytes) => {
          progressDone.value = done
          progressTotal.value = totalBytes
        }
      }
    )
    const objUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objUrl
    a.download = displayName.value
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(objUrl), 30_000)
    snackbar({ message: '已开始下载' })
  } catch (e) {
    console.error('download failed:', e)
    snackbar({ message: `下载失败: ${e instanceof Error ? e.message : String(e)}`, closeable: true })
  } finally {
    isBusy.value = false
  }
}

function goBackToPaste() {
  router.push(`/p/${encodeURIComponent(pasteId.value)}${window.location.hash}`)
}

onMounted(async () => {
  isLoading.value = true
  error.value = ''
  await loadMetaAndManifest()
  isLoading.value = false
})
</script>

<style scoped>
.file-download-view {
  padding-top: 2rem;
  padding-bottom: 2rem;
}

.loading-indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.error-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 8px;
  background-color: var(--mdui-color-error-container);
  color: var(--mdui-color-on-error-container);
}

.error-text {
  font-size: 14px;
  line-height: 1.4;
}

.file-card {
  background-color: var(--mdui-color-surface-variant);
  border-radius: 12px;
  padding: 16px;
}

.file-header {
  margin-bottom: 14px;
}

.file-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--mdui-color-on-surface);
  word-break: break-word;
}

.file-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--mdui-color-on-surface-variant);
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
  color: var(--mdui-color-on-surface-variant);
}

.file-meta-row .value {
  color: var(--mdui-color-on-surface);
  word-break: break-all;
}

.video-section {
  margin-top: 14px;
  margin-bottom: 16px;
}

.video-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--mdui-color-on-surface);
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

.video-placeholder {
  padding: 12px;
  border-radius: 10px;
  background-color: var(--mdui-color-surface);
  color: var(--mdui-color-on-surface-variant);
  font-size: 13px;
  line-height: 1.6;
}

.video-placeholder .hint {
  margin-top: 6px;
}

.progress-section {
  margin-top: 10px;
  margin-bottom: 10px;
}

.progress-text {
  margin-top: 6px;
  font-size: 12px;
  color: var(--mdui-color-on-surface-variant);
  text-align: right;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 14px;
}

/* Dialog 样式（与 PasteViewer 一致） */
.dialog-content {
  padding: 16px 0;
}

.dialog-description {
  font-size: 14px;
  color: var(--mdui-color-on-surface-variant);
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.config-section {
  margin-bottom: 20px;
}

.warning-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: var(--mdui-color-error-container);
  color: var(--mdui-color-on-error-container);
  border-radius: 8px;
  margin-top: 8px;
}

.warning-message mdui-icon {
  flex-shrink: 0;
  font-size: 20px;
}

.warning-message p {
  margin: 0;
  font-size: 14px;
}
</style>
