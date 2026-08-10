import { computed, nextTick, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { snackbar } from 'mdui/functions/snackbar.js'
import {
  abortFileUpload,
  completeFileUpload,
  deleteFile,
  getFileUploadStatus,
  initFileUpload,
  uploadFileChunk
} from '../services/paste'
import { DEFAULT_UPLOAD_CONCURRENCY, getPublicConfig } from '../services/config'
import { isImageFileName } from './useFile'
import {
  bytesToStr,
  encryptFileChunk,
  encryptWithKey,
  getAesGcmEncryptedLength
} from '../utils/crypto'
import type { FailedFile, UploadedFile, UploadingFile } from '../components/upload/types'

export type ProcessFilesOpts = { autoInsert?: boolean; source?: 'paste' | 'select' | 'drop' }
export type AutoInsertPayload = { fileId: string; name: string; size: number }
type UploadOutcome = 'success' | 'failed' | 'cancelled'

const HASH_DEDUPE_MAX_BYTES = 10 * 1024 * 1024 // 10MB
const UPLOAD_SPEED_UPDATE_MIN_INTERVAL_SEC = 0.1

function fileFingerprintParts(name: string, size: number, lastModified: number): string {
  return `${name}::${size}::${lastModified}`
}

function fileFingerprint(file: File): string {
  return fileFingerprintParts(file.name, file.size, file.lastModified)
}

async function sha256HexOfFile(file: File): Promise<string> {
  const buf = await file.arrayBuffer()
  const digest = await crypto.subtle.digest('SHA-256', buf)
  const bytes = new Uint8Array(digest)
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

function isLikelyImageFile(file: File): boolean {
  if (file.type && file.type.startsWith('image/')) return true
  return isImageFileName(file.name)
}

async function computeDedupeFingerprint(
  file: File,
  source?: 'paste' | 'select' | 'drop'
): Promise<string> {
  const shouldHash =
    file.size > 0 &&
    file.size <= HASH_DEDUPE_MAX_BYTES &&
    (source === 'paste' || isLikelyImageFile(file))
  if (shouldHash) {
    try {
      const hex = await sha256HexOfFile(file)
      return `sha256:${hex}`
    } catch {
      // 继续走下面的元信息去重分支
    }
  }

  if (source === 'paste') {
    // Clipboard生成的File通常lastModified会变化；用稳定元信息兜底去重
    return `paste:${file.name}::${file.size}::${file.type || ''}`
  }

  return `file:${fileFingerprint(file)}`
}

function formatSkippedFileNames(files: File[], maxNames: number = 3): string {
  const names = files.map((f) => f.name)
  if (names.length <= maxNames) return names.join('、')
  return `${names.slice(0, maxNames).join('、')} 等`
}

function calcStoredBytesForAesGcmChunks(
  plainSize: number,
  chunkSize: number,
  totalChunks: number
): number {
  if (!Number.isFinite(plainSize) || plainSize < 0) return 0
  if (!Number.isFinite(chunkSize) || chunkSize <= 0) return plainSize
  if (!Number.isFinite(totalChunks) || totalChunks <= 0) return plainSize

  let total = 0
  for (let i = 0; i < totalChunks; i++) {
    const start = i * chunkSize
    const plainLen = Math.max(0, Math.min(chunkSize, plainSize - start))
    total += getAesGcmEncryptedLength(plainLen)
  }
  return total
}

function isChunkAlreadyExistsError(error: unknown): boolean {
  const err = error as any
  const detail = err?.response?.data?.detail
  return err?.response?.status === 400 && typeof detail === 'string' && detail.includes('分片已存在')
}

function createSemaphore(maxConcurrent: number) {
  let active = 0
  const waiters: Array<{
    resolve: (release: () => void) => void
    reject: (err: unknown) => void
    signal?: AbortSignal
    onAbort?: () => void
  }> = []

  const release = () => {
    active = Math.max(0, active - 1)
    dispatch()
  }

  const dispatch = () => {
    while (active < maxConcurrent && waiters.length > 0) {
      const w = waiters.shift()!
      if (w.onAbort && w.signal) {
        w.signal.removeEventListener('abort', w.onAbort)
      }
      if (w.signal?.aborted) {
        w.reject(new DOMException('Upload cancelled', 'AbortError'))
        continue
      }
      active += 1
      w.resolve(release)
    }
  }

  const acquire = (signal?: AbortSignal): Promise<() => void> => {
    if (signal?.aborted) {
      return Promise.reject(new DOMException('Upload cancelled', 'AbortError'))
    }
    if (active < maxConcurrent) {
      active += 1
      return Promise.resolve(release)
    }
    return new Promise((resolve, reject) => {
      const waiter = { resolve, reject, signal } as (typeof waiters)[number]
      if (signal) {
        const onAbort = () => {
          const idx = waiters.indexOf(waiter)
          if (idx >= 0) {
            waiters.splice(idx, 1)
            reject(new DOMException('Upload cancelled', 'AbortError'))
          }
        }
        waiter.onAbort = onAbort
        signal.addEventListener('abort', onAbort, { once: true })
      }
      waiters.push(waiter)
    })
  }

  return { acquire }
}

export function useFileUploader(params: {
  pasteId: Ref<string>
  adminKey: Ref<string>
  encryptionKey: Ref<Uint8Array | null>
  maxTotalUploadSize: Ref<number | null>
  remainingUploadSize: Ref<number | null>
  onEnsurePaste: () => Promise<boolean>
  onAutoInsert?: (file: AutoInsertPayload) => void
}) {
  const uploadingFiles = ref<UploadingFile[]>([])
  const uploadedFiles = ref<UploadedFile[]>([])
  const failedFiles = ref<FailedFile[]>([])
  const cancelledUploads = new Set<string>()

  const uploadSemaphore = createSemaphore(DEFAULT_UPLOAD_CONCURRENCY)

  // 动态配置
  const maxFileSize = ref(10 * 1024 * 1024) // 默认 10MB
  const maxChunkSize = ref(2 * 1024 * 1024) // 默认 2MB

  const maxTotalUploadBytes = ref<number | null>(params.maxTotalUploadSize.value ?? null)
  const remainingUploadBytes = ref<number | null>(params.remainingUploadSize.value ?? null)

  watch(
    () => params.maxTotalUploadSize.value,
    (v) => {
      if (typeof v === 'number') maxTotalUploadBytes.value = v
    }
  )
  watch(
    () => params.remainingUploadSize.value,
    (v) => {
      if (v === null || typeof v === 'number') remainingUploadBytes.value = v
    }
  )

  function updateCapacityFromServer(
    max: number | undefined,
    remaining: number | null | undefined,
    opts: { allowIncrease: boolean }
  ) {
    if (typeof max === 'number') {
      maxTotalUploadBytes.value = max
    }
    if (remaining === undefined) return

    if (remaining === null || typeof remaining === 'number') {
      const current = remainingUploadBytes.value
      if (
        !opts.allowIncrease &&
        typeof current === 'number' &&
        typeof remaining === 'number' &&
        remaining > current
      ) {
        return
      }
      remainingUploadBytes.value = remaining
    }
  }

  function formatBytes(bytes: number): string {
    if (!Number.isFinite(bytes) || bytes < 0) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  const capacityMaxBytes = computed(() => maxTotalUploadBytes.value)
  const capacityUsedBytes = computed(() => {
    const max = maxTotalUploadBytes.value
    const remaining = remainingUploadBytes.value
    if (typeof max !== 'number' || max <= 0) return null
    if (typeof remaining !== 'number') return null
    return Math.max(0, Math.min(max, max - remaining))
  })

  const showCapacity = computed(() => !!params.pasteId.value && maxTotalUploadBytes.value !== null)
  const showCapacityBar = computed(() => {
    const max = capacityMaxBytes.value
    const used = capacityUsedBytes.value
    return typeof max === 'number' && max > 0 && typeof used === 'number'
  })

  const capacityText = computed(() => {
    const max = maxTotalUploadBytes.value
    const remaining = remainingUploadBytes.value
    if (max === null) return '加载中…'
    if (max === 0) return '不限'
    if (typeof remaining !== 'number') return `0 / ${formatBytes(max)}`
    const used = Math.max(0, Math.min(max, max - remaining))
    return `${formatBytes(used)} / ${formatBytes(max)}`
  })

  function showUploadSummary(results: UploadOutcome[]) {
    const uploadedCount = results.filter((result) => result === 'success').length
    const failedCount = results.filter((result) => result === 'failed').length
    if (uploadedCount === 0 && failedCount === 0) return

    snackbar({
      message:
        failedCount > 0
          ? `已上传 ${uploadedCount} 个文件，${failedCount} 个文件失败`
          : `已上传 ${uploadedCount} 个文件`,
      closeable: failedCount > 0
    })
  }

  async function startUpload(
    file: File,
    options?: { id?: string; resumeUploadId?: string; autoInsert?: boolean; fingerprint?: string }
  ): Promise<UploadOutcome> {
    const id = options?.id ?? crypto.randomUUID()
    const abortController = new AbortController()
    const uploadingFile: UploadingFile = {
      id,
      name: file.name,
      size: file.size,
      progress: 0,
      speed: 0,
      state: 'queued',
      file,
      abortController,
      fingerprint: options?.fingerprint
    }
    let lastTime = Date.now()
    let lastLoaded = 0
    uploadingFiles.value.push(uploadingFile)

    let releaseSlot: (() => void) | null = null
    let didAutoInsert = false
    try {
      if (!params.encryptionKey.value) {
        throw new Error('加密密钥未就绪')
      }

      const throwIfAborted = () => {
        if (abortController.signal.aborted) {
          throw new DOMException('Upload cancelled', 'AbortError')
        }
      }

      throwIfAborted()
      releaseSlot = await uploadSemaphore.acquire(abortController.signal)
      uploadingFile.state = 'uploading'

      // 加密文件名
      const encryptedNameBytes = await encryptWithKey(file.name, params.encryptionKey.value)
      const encryptedName = bytesToStr(encryptedNameBytes)

      let upload_id: string | null = null
      let chunk_size = 0
      let total_chunks = 0
      const uploadedChunks = new Set<number>()

      // 断点续传：优先复用已有 uploadId
      if (options?.resumeUploadId) {
        try {
          const status = await getFileUploadStatus(
            params.pasteId.value,
            params.adminKey.value,
            options.resumeUploadId,
            abortController.signal
          )
          if (status.encryption_mode !== 'client') {
            throw new Error('加密模式不匹配')
          }
          if (status.file_size !== file.size) {
            throw new Error('文件大小与上传会话不匹配')
          }
          upload_id = options.resumeUploadId
          chunk_size = status.chunk_size
          total_chunks = status.total_chunks
          for (const idx of status.uploaded_chunks || []) uploadedChunks.add(idx)
          uploadingFile.uploadId = upload_id
          uploadingFile.progress = Math.round((uploadedChunks.size / total_chunks) * 100)
          lastTime = Date.now()
          lastLoaded = Math.min(status.next_index * chunk_size, file.size)
          updateCapacityFromServer(status.max_total_upload_size, status.remaining_upload_size, {
            allowIncrease: true
          })
        } catch (e) {
          console.warn('Resume status failed, re-init upload session:', e)
        }
      }

      // 初始化上传（新会话）
      if (!upload_id) {
        const initRes = await initFileUpload(
          params.pasteId.value,
          params.adminKey.value,
          {
            encryption_mode: 'client',
            file_name: encryptedName,
            mime_type: file.type || 'application/octet-stream',
            file_size: file.size,
            requested_chunk_size: maxChunkSize.value
          },
          undefined,
          abortController.signal
        )

        uploadingFile.uploadId = initRes.upload_id
        upload_id = initRes.upload_id
        chunk_size = initRes.chunk_size
        total_chunks = initRes.total_chunks
        updateCapacityFromServer(initRes.max_total_upload_size, initRes.remaining_upload_size, {
          allowIncrease: false
        })
      }

      if (!upload_id) {
        throw new Error('上传会话未初始化')
      }
      const sessionUploadId = upload_id

      // 分片上传
      for (let i = 0; i < total_chunks; i++) {
        throwIfAborted()
        if (uploadedChunks.has(i)) continue
        const start = i * chunk_size
        const end = Math.min(start + chunk_size, file.size)
        const chunkData = new Uint8Array(await file.slice(start, end).arrayBuffer())

        // 加密分片
        const encryptedChunk = await encryptFileChunk(chunkData, params.encryptionKey.value, {
          pasteId: params.pasteId.value,
          uploadId: sessionUploadId,
          fileId: sessionUploadId,
          chunkIndex: i,
          totalChunks: total_chunks
        })

        // 上传分片
        throwIfAborted()
        const baseCompleted = uploadedChunks.size
        try {
          await uploadFileChunk(
            params.pasteId.value,
            params.adminKey.value,
            sessionUploadId,
            i,
            encryptedChunk,
            (loaded, total) => {
              const file = uploadingFiles.value.find((f) => f.id === id)
              if (file) {
                const chunkProgress = total > 0 ? loaded / total : 0
                file.progress = Math.round(((baseCompleted + chunkProgress) / total_chunks) * 100)
                const now = Date.now()
                const totalLoaded = start + loaded
                const timeDiff = (now - lastTime) / 1000
                if (timeDiff > UPLOAD_SPEED_UPDATE_MIN_INTERVAL_SEC) {
                  file.speed = (totalLoaded - lastLoaded) / timeDiff
                  lastTime = now
                  lastLoaded = totalLoaded
                }
              }
            },
            abortController.signal
          )
        } catch (e) {
          if (!isChunkAlreadyExistsError(e)) throw e
        }
        uploadedChunks.add(i)
        const current = uploadingFiles.value.find((f) => f.id === id)
        if (current) current.progress = Math.round((uploadedChunks.size / total_chunks) * 100)
      }

      // 完成上传
      throwIfAborted()
      const completeRes = await completeFileUpload(
        params.pasteId.value,
        params.adminKey.value,
        sessionUploadId,
        {},
        undefined,
        abortController.signal
      )
      updateCapacityFromServer(completeRes.max_total_upload_size, completeRes.remaining_upload_size, {
        allowIncrease: true
      })

      const storedSize = calcStoredBytesForAesGcmChunks(file.size, chunk_size, total_chunks)

      // 移动到已上传列表
      uploadingFiles.value = uploadingFiles.value.filter((f) => f.id !== id)
      uploadedFiles.value.push({
        id,
        fileId: completeRes.file_id,
        name: file.name,
        size: file.size,
        storedSize,
        lastModified: file.lastModified,
        fingerprint: uploadingFile.fingerprint ?? `file:${fileFingerprint(file)}`
      })

      if (options?.autoInsert && params.onAutoInsert && !didAutoInsert) {
        params.onAutoInsert({ fileId: completeRes.file_id, name: file.name, size: file.size })
      }
      return 'success'
    } catch (error) {
      const isCancelled =
        cancelledUploads.has(id) ||
        abortController.signal.aborted ||
        (typeof error === 'object' &&
          error !== null &&
          'code' in error &&
          (error as any).code === 'ERR_CANCELED') ||
        (typeof error === 'object' &&
          error !== null &&
          'name' in error &&
          ((error as any).name === 'CanceledError' || (error as any).name === 'AbortError'))

      if (isCancelled) {
        uploadingFiles.value = uploadingFiles.value.filter((f) => f.id !== id)
        if (!cancelledUploads.has(id) && uploadingFile.uploadId) {
          try {
            await abortFileUpload(params.pasteId.value, params.adminKey.value, uploadingFile.uploadId)
          } catch (e) {
            console.error('Abort failed:', e)
          }
        }
        cancelledUploads.delete(id)
        return 'cancelled'
      }

      console.error('Upload failed:', error)
      uploadingFiles.value = uploadingFiles.value.filter((f) => f.id !== id)
      failedFiles.value.push({
        id,
        name: file.name,
        size: file.size,
        error: error instanceof Error ? error.message : '上传失败',
        file,
        uploadId: uploadingFile.uploadId,
        fingerprint: uploadingFile.fingerprint
      })
      return 'failed'
    } finally {
      releaseSlot?.()
    }
  }

  async function processFiles(files: File[], opts?: ProcessFilesOpts) {
    const maxSize = maxFileSize.value
    const maxSizeMB = (maxSize / 1024 / 1024).toFixed(0)
    const validFiles = files.filter((file) => {
      if (file.size > maxSize) {
        snackbar({ message: `文件 ${file.name} 超过 ${maxSizeMB}MB 限制`, closeable: true })
        return false
      }
      return true
    })

    if (validFiles.length === 0) return

    // 前端去重：避免同一会话重复上传相同本地文件（不做内容级校验）
    const existingFingerprints = new Set<string>()
    for (const f of uploadingFiles.value) {
      existingFingerprints.add(f.fingerprint ?? `file:${fileFingerprint(f.file)}`)
    }
    for (const f of failedFiles.value) {
      existingFingerprints.add(f.fingerprint ?? `file:${fileFingerprint(f.file)}`)
    }
    for (const f of uploadedFiles.value) existingFingerprints.add(f.fingerprint)

    const seenFingerprints = new Set<string>()
    const dedupedFiles: File[] = []
    const skippedFiles: File[] = []
    const fingerprintsByFile = new Map<File, string>()
    for (const file of validFiles) {
      const fp = await computeDedupeFingerprint(file, opts?.source)
      fingerprintsByFile.set(file, fp)
      if (seenFingerprints.has(fp) || existingFingerprints.has(fp)) {
        skippedFiles.push(file)
        continue
      }
      seenFingerprints.add(fp)
      dedupedFiles.push(file)
    }

    if (skippedFiles.length > 0) {
      const msg =
        skippedFiles.length === 1
          ? `已跳过重复文件：${skippedFiles[0]!.name}`
          : `已跳过 ${skippedFiles.length} 个重复文件：${formatSkippedFileNames(skippedFiles)}`
      snackbar({ message: msg, closeable: true })
    }

    if (dedupedFiles.length === 0) return

    // 确保 Paste 已创建
    if (!params.pasteId.value || !params.adminKey.value || !params.encryptionKey.value) {
      const ready = await params.onEnsurePaste()
      if (!ready) {
        snackbar({ message: '创建 Paste 失败', closeable: true })
        return
      }
      await nextTick()
      if (!params.pasteId.value || !params.adminKey.value || !params.encryptionKey.value) {
        snackbar({ message: '上传信息未就绪，请稍后重试', closeable: true })
        return
      }
    }

    const results = await Promise.all(
      dedupedFiles.map((file) =>
        startUpload(file, {
          autoInsert: opts?.autoInsert,
          fingerprint: fingerprintsByFile.get(file),
          resumeUploadId: undefined
        })
      )
    )
    showUploadSummary(results)
  }

  async function cancelUpload(id: string) {
    const file = uploadingFiles.value.find((f) => f.id === id)
    cancelledUploads.add(id)
    file?.abortController?.abort()
    if (file?.uploadId) {
      try {
        await abortFileUpload(params.pasteId.value, params.adminKey.value, file.uploadId)
      } catch (e) {
        console.error('Abort failed:', e)
      }
    }
    if (
      file &&
      typeof remainingUploadBytes.value === 'number' &&
      typeof maxTotalUploadBytes.value === 'number' &&
      maxTotalUploadBytes.value > 0
    ) {
      remainingUploadBytes.value = Math.min(
        maxTotalUploadBytes.value,
        remainingUploadBytes.value + file.size
      )
    }
    uploadingFiles.value = uploadingFiles.value.filter((f) => f.id !== id)
  }

  async function removeFile(id: string) {
    const file = uploadedFiles.value.find((f) => f.id === id)
    if (file) {
      try {
        await deleteFile(params.pasteId.value, params.adminKey.value, file.fileId)
        uploadedFiles.value = uploadedFiles.value.filter((f) => f.id !== id)
        if (
          typeof remainingUploadBytes.value === 'number' &&
          typeof maxTotalUploadBytes.value === 'number' &&
          maxTotalUploadBytes.value > 0
        ) {
          remainingUploadBytes.value = Math.min(
            maxTotalUploadBytes.value,
            remainingUploadBytes.value + file.storedSize
          )
        }
      } catch (e) {
        console.error('Delete file failed:', e)
        snackbar({ message: '删除文件失败', closeable: true })
      }
    }
  }

  async function retryUpload(file: FailedFile) {
    failedFiles.value = failedFiles.value.filter((f) => f.id !== file.id)
    const result = await startUpload(file.file, {
      id: file.id,
      resumeUploadId: file.uploadId,
      fingerprint: file.fingerprint
    })
    showUploadSummary([result])
  }

  function dismissFailed(id: string) {
    failedFiles.value = failedFiles.value.filter((f) => f.id !== id)
  }

  function handlePaste(e: ClipboardEvent) {
    const files = e.clipboardData?.files
    if (files && files.length > 0) {
      e.preventDefault()
      processFiles(Array.from(files), { autoInsert: true, source: 'paste' })
    }
  }

  onMounted(async () => {
    document.addEventListener('paste', handlePaste)
    const config = await getPublicConfig()
    maxFileSize.value = config.max_upload_file_size
    maxChunkSize.value = config.max_chunk_size
  })

  onUnmounted(() => {
    document.removeEventListener('paste', handlePaste)
  })

  return {
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
  }
}
