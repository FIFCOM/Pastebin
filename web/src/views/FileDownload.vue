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
      <div class="file-preview">
        <div v-if="isVideo" class="preview-section">
          <div v-if="videoPlainSrc" class="video-container">
            <video class="video-player" controls preload="metadata" :src="videoPlainSrc"></video>
          </div>
          <PreviewPlaceholder v-else />
        </div>

        <div v-else-if="isImage" class="preview-section">
          <div v-if="imagePlainSrc" class="image-container">
            <img
              class="image-preview"
              :src="imagePlainSrc"
              :alt="displayName"
              title="点击放大"
              @click="openImagePreview"
            />
          </div>
          <PreviewPlaceholder v-else />
        </div>

        <div v-else-if="isAudio" class="preview-section">
          <div v-if="audioPlainSrc" class="audio-container">
            <audio class="audio-player" controls preload="metadata" :src="audioPlainSrc"></audio>
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

      <mdui-card class="file-info-card">
        <div class="file-header">
          <div class="file-header-main">
            <div class="file-title-row">
              <div class="file-title" :title="displayName">{{ displayName }}</div>
              <mdui-chip
                v-if="encryptionLabel"
                class="encryption-chip"
                variant="tonal"
                :class="`mode-${encryptionMode}`"
                title="加密状态"
              >
                <mdui-icon name="lock" class="encryption-chip-icon"></mdui-icon>
                <span>{{ encryptionLabel }}</span>
              </mdui-chip>
            </div>
            <div class="file-subtitle">{{ meta?.mime_type || 'application/octet-stream' }}</div>
          </div>

          <div class="file-header-actions">
            <mdui-button-icon
              :icon="shareUrlCopied ? 'check' : 'content_copy'"
              :disabled="!shareUrl"
              :title="shareUrlCopied ? '已复制' : '复制分享链接'"
              @click="copyShareUrl"
            ></mdui-button-icon>
          </div>
        </div>

        <div class="file-meta">
          <div class="file-meta-row">
            <span class="label">大小</span>
            <span class="value">{{ humanSize(plainSize || 0) }}</span>
          </div>

          <div v-if="meta?.created_at" class="file-meta-row">
            <span class="label">上传时间</span>
            <span class="value">{{ formatDateTime(meta?.created_at) }}</span>
          </div>

          <div v-if="pasteInfo" class="file-meta-row">
            <span class="label">过期时间</span>
            <span class="value">{{ pasteExpireText }}</span>
          </div>

          <div v-if="pasteInfo" class="file-meta-row">
            <span class="label">查看次数</span>
            <span class="value">{{ pasteViewsText }}</span>
          </div>
        </div>

        <div v-if="showProgress" class="progress-section">
          <mdui-linear-progress
            class="download-progress"
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
            @click="handleDownload"
          >
            <mdui-icon slot="icon" name="download"></mdui-icon>
            {{ isDownloading ? '下载中' : downloadState === 'done' ? '重新下载' : '下载' }}
          </mdui-button>
        </div>
      </mdui-card>
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
import PreviewPlaceholder from '@/components/common/PreviewPlaceholder.vue'
import { useDownloadProgress } from '@/composables/useDownloadProgress'
import {
  buildAccessKeyQuery,
  getPublicFileManifest,
  getPublicFileMeta,
  getPublicPasteInfo,
  type PublicFileMeta,
  type PublicPasteInfo
} from '@/services/publicApi'
import { formatDateTime, formatDurationSeconds, humanSize } from '@/utils/format'

import 'mdui/components/card.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/chip.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/dialog.js'
import 'mdui/components/icon.js'
import 'mdui/components/linear-progress.js'
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
const downloadState = ref<'idle' | 'downloading' | 'done' | 'error'>('idle')
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
const displayName = computed(() => decryptedName.value || `mb_encrypted_${fileId.value}`)
const mimeType = computed(() => meta.value?.mime_type || 'application/octet-stream')
const isVideo = computed(() => mimeType.value.startsWith('video/'))
const isImage = computed(() => mimeType.value.startsWith('image/'))
const isAudio = computed(() => mimeType.value.startsWith('audio/'))

function getFileExt(name: string): string {
  const base = (name || '').trim()
  const idx = base.lastIndexOf('.')
  if (idx <= 0 || idx >= base.length - 1) return ''
  return base.slice(idx + 1).toLowerCase()
}

function isProbablyText(mime: string, name: string): boolean {
  const mt = (mime || '').toLowerCase().trim()
  if (mt.startsWith('text/')) return true
  if (
    mt === 'application/json' ||
    mt === 'application/xml' ||
    mt === 'application/yaml' ||
    mt === 'application/x-yaml' ||
    mt === 'application/toml'
  ) {
    return true
  }

  const ext = getFileExt(name)
  return (
    ext === 'txt' ||
    ext === 'md' ||
    ext === 'json' ||
    ext === 'csv' ||
    ext === 'log' ||
    ext === 'yaml' ||
    ext === 'yml' ||
    ext === 'toml' ||
    ext === 'ini' ||
    ext === 'conf' ||
    ext === 'xml'
  )
}

const isText = computed(() => isProbablyText(mimeType.value, displayName.value))

function fileTypeToIconName(mime: string, name: string): string {
  const mt = (mime || '').toLowerCase().trim()
  const ext = getFileExt(name)

  // PDF
  if (mt === 'application/pdf' || ext === 'pdf') return 'picture_as_pdf'

  // Archives / compressed files
  if (
    mt === 'application/zip' ||
    mt === 'application/x-7z-compressed' ||
    mt === 'application/x-rar-compressed' ||
    mt === 'application/vnd.rar' ||
    mt === 'application/x-tar' ||
    mt === 'application/gzip' ||
    mt === 'application/x-gzip' ||
    mt === 'application/x-bzip2' ||
    mt === 'application/x-xz' ||
    mt === 'application/zstd' ||
    ext === 'zip' ||
    ext === 'rar' ||
    ext === '7z' ||
    ext === 'tar' ||
    ext === 'gz' ||
    ext === 'tgz' ||
    ext === 'bz2' ||
    ext === 'xz' ||
    ext === 'zst' ||
    ext === 'lz' ||
    ext === 'lz4'
  ) {
    return 'folder_zip'
  }

  // Office docs / documents
  if (
    mt === 'application/msword' ||
    mt === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    mt === 'application/vnd.oasis.opendocument.text' ||
    ext === 'doc' ||
    ext === 'docx' ||
    ext === 'odt' ||
    ext === 'wps' ||
    ext === 'pages'
  ) {
    return 'description'
  }

  // Spreadsheets
  if (
    mt === 'application/vnd.ms-excel' ||
    mt === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    mt === 'application/vnd.oasis.opendocument.spreadsheet' ||
    ext === 'xls' ||
    ext === 'xlsx' ||
    ext === 'ods' ||
    ext === 'numbers'
  ) {
    return 'table_chart'
  }

  // Presentations
  if (
    mt === 'application/vnd.ms-powerpoint' ||
    mt === 'application/vnd.openxmlformats-officedocument.presentationml.presentation' ||
    mt === 'application/vnd.oasis.opendocument.presentation' ||
    ext === 'ppt' ||
    ext === 'pptx' ||
    ext === 'odp' ||
    ext === 'key'
  ) {
    return 'slideshow'
  }

  // Fonts
  if (
    mt.startsWith('font/') ||
    mt === 'application/font-woff' ||
    mt === 'application/font-woff2' ||
    ext === 'ttf' ||
    ext === 'otf' ||
    ext === 'woff' ||
    ext === 'woff2'
  ) {
    return 'font_download'
  }

  return 'insert_drive_file'
}

const fileTypeIcon = computed(() => fileTypeToIconName(mimeType.value, displayName.value))

const encryptionMode = computed(() => {
  const m = String(manifest.value?.encryption_mode || '').toLowerCase()
  return m === 'client' || m === 'server' ? m : ''
})
const encryptionLabel = computed(() => {
  if (encryptionMode.value === 'client') return '端到端加密'
  if (encryptionMode.value === 'server') return '加密'
  return ''
})

const pasteExpireText = computed(() => {
  const v = pasteInfo.value?.expire_at ?? null
  if (!v) return '永不过期'
  return formatDateTime(v)
})

const pasteViewsText = computed(() => {
  const maxViews = Number(pasteInfo.value?.max_views)
  const viewCount = Number(pasteInfo.value?.view_count)
  const max = Number.isFinite(maxViews) ? maxViews : -1
  const cnt = Number.isFinite(viewCount) && viewCount >= 0 ? viewCount : 0

  if (max <= 0) return `${cnt}（无限制）`
  const left = Math.max(0, max - cnt)
  return `${cnt} / ${max}（剩余 ${left} 次）`
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
  background-color: var(--mdui-color-error-container);
  color: var(--mdui-color-on-error-container);
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

.file-preview {
  flex: 1 1 0;
  min-width: 0;
}

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
  color: var(--mdui-color-on-surface);
  flex: 1 1 auto;
  min-width: 0; /* allow shrinking inside flex so the chip stays visible */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@supports (-webkit-line-clamp: 2) {
  .file-title {
    white-space: normal;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }
}

.file-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.encryption-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

.encryption-chip-icon {
  font-size: 18px;
}

.encryption-chip.mode-client .encryption-chip-icon {
  color: rgb(var(--mdui-color-tertiary));
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
  background-color: var(--mdui-color-surface);
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
  background-color: var(--mdui-color-surface);
  padding: 12px;
}

.audio-player {
  width: 100%;
}

.text-preview-container {
  border-radius: 10px;
  background-color: var(--mdui-color-surface);
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
  color: var(--mdui-color-on-surface);
}

.text-preview-subtitle {
  font-size: 12px;
  color: var(--mdui-color-on-surface-variant);
  white-space: nowrap;
}

.text-preview-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  color: var(--mdui-color-on-surface-variant);
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
  color: var(--mdui-color-on-surface-variant);
}

.file-icon-section {
  border-radius: 12px;
  background-color: var(--mdui-color-surface-variant);
  padding: 32px 16px;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--mdui-color-on-surface-variant);
  gap: 12px;
}

.file-icon {
  font-size: 64px;
}

.file-icon-name {
  font-size: 14px;
  color: var(--mdui-color-on-surface);
  word-break: break-word;
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

.download-progress {
  --mdui-motion-duration-long2: 0ms;
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
  .file-download-layout {
    flex-direction: column;
  }

  .file-info-card {
    width: 100%;
    order: -1;
  }

  .file-preview {
    width: 100%;
  }
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
