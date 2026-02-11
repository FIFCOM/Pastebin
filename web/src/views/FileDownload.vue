<template>
  <div class="file-download-view">
    <div v-if="isLoading" class="loading-indicator">
      <mdui-circular-progress></mdui-circular-progress>
    </div>

    <div v-else-if="error" class="error-box">
      <mdui-icon name="error"></mdui-icon>
      <div class="error-text">{{ error }}</div>
    </div>

    <div v-else class="file-download-layout">
      <FilePreviewPanel
        :is-video="isVideo"
        :is-image="isImage"
        :is-audio="isAudio"
        :is-text="isText"
        :video-src="videoPlainSrc"
        :image-src="imagePlainSrc"
        :audio-src="audioPlainSrc"
        :display-name="displayName"
        :file-type-icon="fileTypeIcon"
        :text-preview-label="textPreviewLabel"
        :text-preview-loading="textPreviewLoading"
        :text-preview-error="textPreviewError"
        :text-preview="textPreview"
        :text-preview-truncated="textPreviewTruncated"
        @image-preview="openImagePreview"
      />

      <FileInfoCard
        :display-name="displayName"
        :encryption-label="encryptionLabel"
        :encryption-mode="encryptionMode"
        :share-url="shareUrl"
        :share-url-copied="shareUrlCopied"
        :plain-size-text="plainSizeText"
        :created-at-text="createdAtText"
        :has-created-at="Boolean(meta?.created_at)"
        :has-paste-info="Boolean(pasteInfo)"
        :paste-expire-text="pasteExpireText"
        :show-progress="showProgress"
        :progress-value="progressValue"
        :progress-text="progressText"
        :is-downloading="isDownloading"
        :download-state="downloadState"
        @copy-share-url="copyShareUrl"
        @download="handleDownload"
      />
    </div>

    <ImagePreview
      v-model:open="imagePreviewOpen"
      :src="imagePreviewSrc"
      :alt="imagePreviewAlt"
      :loading="imagePreviewLoading"
      :error="imagePreviewError"
      @close="closeImagePreview"
    />

    <!-- Access Key 输入对话框 -->
    <mdui-dialog
      ref="accessKeyDialog"
      headline="需要访问密钥"
      close-on-esc="false"
      close-on-overlay-click="false"
    >
      <mdui-icon slot="icon" name="lock" style="color: rgb(var(--mdui-color-primary));"></mdui-icon>
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

    <mdui-dialog ref="downloadDoneDialog" :headline="downloadDoneTitle">
      <mdui-icon
        slot="icon"
        name="check_circle"
        style="color: rgb(var(--mdui-color-tertiary));"
      ></mdui-icon>
      <div class="dialog-content">
        <p class="dialog-description">{{ downloadDoneMessage }}</p>
      </div>
      <mdui-button slot="action" variant="tonal" @click="closeDownloadDoneDialog">
        关闭
      </mdui-button>
    </mdui-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import { useTheme } from '@/composables/useTheme'
import { buildFileChunkAad, decryptWithKey, strToBytes, urlSafeStrToKey } from '@/utils/crypto'
import type { MbFileManifest } from '@/utils/mbFileDecrypt'
import { decryptChunkedFileStream, decryptChunkedFileToBlob } from '@/utils/mbFileDecrypt'
import { buildMbPlainFilePath, mbSwSetPasteContext } from '@/utils/mbSw'
import ImagePreview from '@/components/common/ImagePreview.vue'
import FileInfoCard from '@/components/file-download/FileInfoCard.vue'
import FilePreviewPanel from '@/components/file-download/FilePreviewPanel.vue'
import type { DownloadState } from '@/components/file-download/types'
import { useDownloadProgress } from '@/composables/useDownloadProgress'
import {
  buildAccessKeyQuery,
  getPublicFileManifest,
  getPublicFileMeta,
  getPublicPasteInfo,
  type PublicFileMeta,
  type PublicPasteInfo
} from '@/services/publicApi'
import { fileTypeToIconName, isProbablyText } from '@/utils/fileTypeIcon'
import { formatDate, formatDurationSeconds, humanSize } from '@/utils/format'

import 'mdui/components/button.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/dialog.js'
import 'mdui/components/icon.js'
import 'mdui/components/text-field.js'

useTheme()

const route = useRoute()
const pasteId = computed(() => route.params.paste_id as string)
const fileId = computed(() => route.params.file_id as string)

const isLoading = ref(true)
const error = ref('')

const pasteInfo = ref<PublicPasteInfo | null>(null)
const meta = ref<PublicFileMeta | null>(null)
const manifest = ref<MbFileManifest | null>(null)

const encryptionKeyBytes = ref<Uint8Array | null>(null)
const decryptedName = ref<string>('')

const accessKey = ref<string | null>(null)
const accessKeyDialog = ref<any>(null)
const accessKeyInput = ref('')
const accessKeyError = ref(false)

const downloadProgress = useDownloadProgress()
const downloadState = ref<DownloadState>('idle')
const isDownloading = computed(() => downloadState.value === 'downloading')
const showProgress = computed(() => downloadState.value !== 'idle')

const videoPlainSrc = ref<string>('')
const imagePlainSrc = ref<string>('')
const audioPlainSrc = ref<string>('')

const imagePreviewOpen = ref(false)
const imagePreviewSrc = ref('')
const imagePreviewAlt = ref('')
const imagePreviewLoading = ref(false)
const imagePreviewError = ref('')

const downloadDoneDialog = ref<any>(null)
const downloadDoneTitle = ref('下载完成')
const downloadDoneMessage = ref('')

const textPreview = ref('')
const textPreviewLoading = ref(false)
const textPreviewError = ref('')
const textPreviewTruncated = ref(false)
let textPreviewTicket = 0

const TEXT_PREVIEW_MAX_PLAIN_BYTES = 16 * 1024

const plainSize = computed(() => manifest.value?.plain_size ?? meta.value?.plain_size ?? 0)
const plainSizeText = computed(() => humanSize(plainSize.value || 0))
const createdAtText = computed(() => {
  if (!meta.value?.created_at) return ''
  return formatDate(meta.value.created_at)
})
const displayName = computed(() => decryptedName.value || `mb_encrypted_${fileId.value}`)
const mimeType = computed(() => meta.value?.mime_type || 'application/octet-stream')
const isVideo = computed(() => mimeType.value.startsWith('video/'))
const isImage = computed(() => mimeType.value.startsWith('image/'))
const isAudio = computed(() => mimeType.value.startsWith('audio/'))

const isText = computed(() => isProbablyText(mimeType.value, displayName.value))

const fileTypeIcon = computed(() => fileTypeToIconName(mimeType.value, displayName.value))

const encryptionMode = computed(() => {
  const m = String(manifest.value?.encryption_mode || '').toLowerCase()
  return m === 'client' || m === 'server' ? m : ''
})
const encryptionLabel = computed(() => {
  if (encryptionMode.value === 'client') return '已端到端加密'
  if (encryptionMode.value === 'server') return '已加密'
  return ''
})

const pasteExpireText = computed(() => {
  const v = pasteInfo.value?.expire_at ?? null
  if (!v) return '永不过期'
  return formatDate(v)
})

const shareUrl = computed(() => window.location.href)
const shareUrlCopied = ref(false)
let shareUrlCopiedTimer: number | null = null

const progressValue = computed(() => (downloadState.value === 'done' ? 1 : downloadProgress.ratio.value))
const progressText = computed(() => {
  const done = humanSize(downloadProgress.plainDone.value)
  const total = humanSize(downloadProgress.plainTotal.value || plainSize.value || 0)

  const parts = [`${done} / ${total}`]

  if (downloadState.value === 'downloading' && downloadProgress.speedBps.value > 0) {
    parts.push(`${humanSize(downloadProgress.speedBps.value)}/s`)
  }

  const eta = downloadProgress.etaSeconds.value
  if (downloadState.value === 'downloading' && eta !== null && eta > 0) {
    parts.push(`剩余 ${formatDurationSeconds(eta)}`)
  }

  if (downloadState.value === 'done') {
    parts.push('已完成')
  } else if (downloadState.value === 'error') {
    parts.push('下载失败')
  }

  return parts.join(' · ')
})

const textPreviewLabel = computed(() => humanSize(TEXT_PREVIEW_MAX_PLAIN_BYTES))

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

async function loadMetaAndManifest(): Promise<void> {
  if (!pasteId.value || !fileId.value) {
    error.value = 'URL 缺少 paste_id 或 file_id。'
    return
  }
  const key = ensureEncryptionKey()
  if (!key) return

  // Reset transient preview states when reloading.
  videoPlainSrc.value = ''
  imagePlainSrc.value = ''
  audioPlainSrc.value = ''
  closeImagePreview()
  resetTextPreview()

  // Try cached access key (same SPA session).
  if (!accessKey.value) {
    try {
      accessKey.value = sessionStorage.getItem(`mb_access_key:${pasteId.value}`)
    } catch {
      accessKey.value = null
    }
  }

  try {
    const [m, man] = await Promise.all([
      getPublicFileMeta(pasteId.value, fileId.value, accessKey.value),
      getPublicFileManifest(pasteId.value, fileId.value, accessKey.value)
    ])

    meta.value = m
    manifest.value = man
    try {
      pasteInfo.value = await getPublicPasteInfo(pasteId.value, accessKey.value)
    } catch (e) {
      // Non-fatal: file download still works without paste-level info.
      console.warn('load paste info failed:', e)
      pasteInfo.value = null
    }

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

    // Enable SW-based media preview (video/image).
    void enableMediaPreview()
    void loadTextPreview()
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

async function enableMediaPreview(): Promise<void> {
  videoPlainSrc.value = ''
  imagePlainSrc.value = ''
  audioPlainSrc.value = ''
  if (!isVideo.value && !isImage.value && !isAudio.value) return

  const key = ensureEncryptionKey()
  if (!key) return

  const ok = await mbSwSetPasteContext({
    pasteId: pasteId.value,
    encryptionKey: key,
    accessKey: accessKey.value
  })
  if (!ok) {
    snackbar({ message: '当前浏览器暂不支持在线预览，请直接下载文件查看。', closeable: true })
    return
  }

  if (isVideo.value) {
    videoPlainSrc.value = buildMbPlainFilePath(pasteId.value, fileId.value)
  }
  if (isImage.value) {
    imagePlainSrc.value = buildMbPlainFilePath(pasteId.value, fileId.value)
  }
  if (isAudio.value) {
    audioPlainSrc.value = buildMbPlainFilePath(pasteId.value, fileId.value)
  }
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

function getErrorName(e: unknown): string {
  if (!e) return ''
  const anyE = e as any
  return typeof anyE?.name === 'string' ? anyE.name : ''
}

function getErrorMessage(e: unknown): string {
  if (!e) return ''
  if (typeof e === 'string') return e
  const anyE = e as any
  if (typeof anyE?.message === 'string') return anyE.message
  try {
    return String(e)
  } catch {
    return ''
  }
}

function isUserAbortError(e: unknown): boolean {
  const name = getErrorName(e)
  if (name === 'AbortError') return true

  const msg = getErrorMessage(e)
  return !!msg && msg.includes('The user aborted a request')
}

function isFailedToFetchError(e: unknown): boolean {
  const msg = getErrorMessage(e).toLowerCase()
  if (!msg) return false
  // Chromium
  if (msg.includes('failed to fetch')) return true
  // Firefox
  if (msg.includes('networkerror') && msg.includes('fetch')) return true
  // Safari (common wording)
  if (msg.includes('load failed')) return true
  return false
}

function formatDownloadErrorMessage(e: unknown): string {
  if (isFailedToFetchError(e)) {
    return '下载失败: 网络异常，无法连接到服务器（请检查网络后重试）'
  }

  const msg = getErrorMessage(e).trim()
  if (!msg) return '下载失败: 未知错误'
  if (msg.startsWith('下载失败')) return msg
  return `下载失败: ${msg}`
}

async function handleDownload() {
  if (isDownloading.value) return
  const key = ensureEncryptionKey()
  if (!key) return
  if (!meta.value || !manifest.value) {
    snackbar({ message: '文件信息未就绪', closeable: true })
    return
  }

  const url = `${meta.value.url}${buildAccessKeyQuery(accessKey.value)}`
  const plainTotal = Number(manifest.value.plain_size) || 0
  const encryptedTotal = (() => {
    const v = Number(meta.value?.encrypted_size)
    if (Number.isFinite(v) && v > 0) return v
    const overhead = Number(manifest.value?.chunk_overhead_bytes) || 0
    const chunks = Number(manifest.value?.total_chunks) || 0
    return plainTotal + overhead * chunks
  })()

  downloadProgress.reset({ plainTotal, encryptedTotal })
  downloadState.value = 'downloading'
  let writable: any = null
  try {
    const picker = (window as any).showSaveFilePicker
    if (typeof picker === 'function') {
      const handle = await picker({
        suggestedName: displayName.value
      })
      writable = await handle.createWritable()

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
            onPlainDownloadProgress: downloadProgress.onPlainProgress,
            onEncryptedProgress: downloadProgress.onEncryptedProgress
          }
      )) {
        await writable.write(plainChunk)
      }

      await writable.close()
      writable = null
      downloadState.value = 'done'
      openDownloadDoneDialog('下载完成', `已保存到本地：${displayName.value}`)
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
        onPlainDownloadProgress: downloadProgress.onPlainProgress,
        onEncryptedProgress: downloadProgress.onEncryptedProgress
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
    downloadState.value = 'done'
    openDownloadDoneDialog('下载已开始', `已交给浏览器下载：${displayName.value}`)
  } catch (e) {
    if (isUserAbortError(e)) {
      try {
        await writable?.abort?.()
      } catch {
        // Ignore abort cleanup errors.
      }
      writable = null
      downloadProgress.reset()
      downloadState.value = 'idle'
      snackbar({ message: '已取消下载' })
      return
    }

    try {
      await writable?.abort?.()
    } catch {
      // Ignore abort cleanup errors.
    }
    writable = null

    console.error('download failed:', e)
    downloadState.value = 'error'
    snackbar({ message: formatDownloadErrorMessage(e), closeable: true })
  }
}

function openDownloadDoneDialog(title: string, message: string) {
  downloadDoneTitle.value = title
  downloadDoneMessage.value = message
  if (downloadDoneDialog.value) downloadDoneDialog.value.open = true
}

function closeDownloadDoneDialog() {
  if (downloadDoneDialog.value) downloadDoneDialog.value.open = false
}

function openImagePreview() {
  if (!imagePlainSrc.value) return
  imagePreviewAlt.value = displayName.value
  imagePreviewError.value = ''
  imagePreviewLoading.value = false
  imagePreviewOpen.value = true
  imagePreviewSrc.value = imagePlainSrc.value
}

function closeImagePreview() {
  imagePreviewOpen.value = false
  imagePreviewSrc.value = ''
  imagePreviewAlt.value = ''
  imagePreviewLoading.value = false
  imagePreviewError.value = ''
}

async function copyShareUrl() {
  const url = shareUrl.value
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    shareUrlCopied.value = true
    if (shareUrlCopiedTimer !== null) window.clearTimeout(shareUrlCopiedTimer)
    shareUrlCopiedTimer = window.setTimeout(() => {
      shareUrlCopied.value = false
      shareUrlCopiedTimer = null
    }, 1200)
    snackbar({ message: '链接已复制' })
  } catch (e) {
    console.error('copy url failed:', e)
    shareUrlCopied.value = false
    if (shareUrlCopiedTimer !== null) window.clearTimeout(shareUrlCopiedTimer)
    shareUrlCopiedTimer = null
    snackbar({ message: '复制失败', closeable: true })
  }
}

function resetTextPreview() {
  textPreviewTicket += 1
  textPreview.value = ''
  textPreviewLoading.value = false
  textPreviewError.value = ''
  textPreviewTruncated.value = false
}

function calcEncryptedPrefixBytes(man: MbFileManifest, plainPrefixBytes: number): number {
  const plainSizeAll = Math.max(0, Number(man.plain_size) || 0)
  const chunkSize = Math.max(0, Number(man.chunk_size) || 0)
  const totalChunks = Math.max(0, Number(man.total_chunks) || 0)
  const overhead = Math.max(0, Number(man.chunk_overhead_bytes) || 0)
  if (plainSizeAll <= 0 || chunkSize <= 0 || totalChunks <= 0) return 0

  const targetPlain = Math.min(Math.max(0, plainPrefixBytes), plainSizeAll)
  if (targetPlain <= 0) return 0

  const needChunks = Math.min(totalChunks, Math.max(1, Math.ceil(targetPlain / chunkSize)))

  let total = 0
  for (let i = 0; i < needChunks; i += 1) {
    const expectedPlain =
      i < totalChunks - 1 ? chunkSize : Math.max(0, plainSizeAll - chunkSize * (totalChunks - 1))
    total += expectedPlain + overhead
  }
  return total
}

async function loadTextPreview(): Promise<void> {
  const ticket = (textPreviewTicket += 1)

  if (!isText.value) return
  if (!meta.value || !manifest.value) return

  const key = ensureEncryptionKey()
  if (!key) return

  const man = manifest.value
  const plainSizeAll = Math.max(0, Number(man.plain_size) || 0)
  const wantPlain = Math.min(TEXT_PREVIEW_MAX_PLAIN_BYTES, plainSizeAll)
  if (wantPlain <= 0) return

  const encBytesToFetch = calcEncryptedPrefixBytes(man, wantPlain)
  if (encBytesToFetch <= 0) return

  textPreviewLoading.value = true
  textPreviewError.value = ''
  textPreview.value = ''
  textPreviewTruncated.value = plainSizeAll > wantPlain

  try {
    const resp = await fetch(`${meta.value.url}${buildAccessKeyQuery(accessKey.value)}`, {
      cache: 'no-store',
      headers: {
        Range: `bytes=0-${encBytesToFetch - 1}`
      }
    })
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }
    const encrypted = new Uint8Array(await resp.arrayBuffer())

    const chunkSize = Math.max(0, Number(man.chunk_size) || 0)
    const totalChunks = Math.max(0, Number(man.total_chunks) || 0)
    const overhead = Math.max(0, Number(man.chunk_overhead_bytes) || 0)
    const aadRequired = Boolean(man.aad_required)
    if (chunkSize <= 0 || totalChunks <= 0 || overhead <= 0) {
      throw new Error('manifest无效，无法预览')
    }

    let offset = 0
    let plainCollected = 0
    const parts: Uint8Array[] = []

    for (let i = 0; i < totalChunks && plainCollected < wantPlain; i += 1) {
      const expectedPlain =
        i < totalChunks - 1 ? chunkSize : Math.max(0, plainSizeAll - chunkSize * (totalChunks - 1))
      const encryptedLen = expectedPlain + overhead
      if (offset + encryptedLen > encrypted.byteLength) break

      const encChunk = encrypted.slice(offset, offset + encryptedLen)
      offset += encryptedLen

      const aad = aadRequired ? buildFileChunkAad(pasteId.value, fileId.value, i, totalChunks) : undefined
      const plain = await decryptWithKey(encChunk, key, aad ? { aad } : undefined)

      const take = Math.min(plain.byteLength, wantPlain - plainCollected)
      if (take > 0) {
        parts.push(plain.slice(0, take))
        plainCollected += take
      }
    }

    if (ticket !== textPreviewTicket) return

    if (parts.length === 0) {
      throw new Error('预览为空（可能是二进制文件或数据损坏）')
    }

    const merged = (() => {
      let total = 0
      for (const p of parts) total += p.byteLength
      const out = new Uint8Array(total)
      let pos = 0
      for (const p of parts) {
        out.set(p, pos)
        pos += p.byteLength
      }
      return out
    })()

    textPreview.value = new TextDecoder().decode(merged)
    textPreviewLoading.value = false
  } catch (e) {
    if (ticket !== textPreviewTicket) return
    console.error('load text preview failed:', e)
    textPreviewLoading.value = false
    textPreviewError.value = `预览失败：${e instanceof Error ? e.message : String(e)}`
  }
}

onMounted(async () => {
  isLoading.value = true
  error.value = ''
  await loadMetaAndManifest()
  isLoading.value = false
})

onBeforeUnmount(() => {
  if (shareUrlCopiedTimer !== null) window.clearTimeout(shareUrlCopiedTimer)
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
  background-color: rgb(var(--mdui-color-error-container));
  color: rgb(var(--mdui-color-on-error-container));
}

.error-text {
  font-size: 14px;
  line-height: 1.4;
}

.file-download-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

@media (max-width: 900px) {
  .file-download-layout {
    flex-direction: column;
  }
}

/* Dialog 样式（与 PasteViewer 一致） */
.dialog-content {
  padding: 16px 0;
}

.dialog-description {
  font-size: 14px;
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
  background-color: rgb(var(--mdui-color-error-container));
  color: rgb(var(--mdui-color-on-error-container));
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
