<template>
  <div class="paste-view">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-indicator">
      <mdui-circular-progress></mdui-circular-progress>
    </div>


    <!-- Paste 内容 -->
    <div v-else-if="pasteData && decryptedContent" class="paste-content">
      <div class="paste-header">
        <mdui-tooltip :content="viewerType === 'md' ? '切换为纯文本' : '切换为 Markdown'">
          <mdui-button-icon @click="toggleViewerType">
            <mdui-icon-article v-if="viewerType === 'md'"></mdui-icon-article>
            <mdui-icon-code v-else></mdui-icon-code>
          </mdui-button-icon>
        </mdui-tooltip>
        <h1 class="paste-title">{{ pasteTitle }}</h1>
      </div>

      <div class="paste-meta">
        <mdui-tooltip content="浏览次数">
          <span class="meta-item meta-icon"><mdui-icon-remove-red-eye></mdui-icon-remove-red-eye>{{ pasteViewsText }}</span>
        </mdui-tooltip>
        <mdui-tooltip content="创建时间">
          <span class="meta-item meta-icon"><mdui-icon-create></mdui-icon-create>{{ pasteCreatedText }}</span>
        </mdui-tooltip>
        <mdui-tooltip content="过期时间">
          <span class="meta-item meta-icon"><mdui-icon-auto-delete></mdui-icon-auto-delete>{{ pasteExpireInlineText }}</span>
        </mdui-tooltip>
        <mdui-tooltip content="文件列表">
          <button type="button" class="meta-item meta-icon meta-action" @click="openPasteFilesDialog">
            <mdui-icon-folder></mdui-icon-folder>{{ pasteFilesText }}
          </button>
        </mdui-tooltip>
      </div>

      <!-- Plain Viewer -->
      <plain-viewer v-if="viewerType === 'txt'" :content="decryptedContent" />
      
      <!-- Markdown Viewer -->
      <markdown-viewer
        v-else-if="viewerType === 'md'"
        :content="decryptedContent"
        :encryption-key="encryptionKeyBytes"
        :access-key="currentAccessKey"
      />
    </div>

    <!-- 文件列表对话框 -->
    <PasteFilesDialog
      ref="pasteFilesDialog"
      :files="pasteFiles"
      :paste-id="pasteId"
      :encryption-key="encryptionKeyBytes"
      :encryption-key-hash="encryptionKeyHash"
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
        <p class="dialog-description">此 Paste 受访问密钥保护，请输入密钥以查看内容。</p>
        
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

    <!-- 错误对话框 -->
    <mdui-dialog
      ref="errorDialog"
      headline="错误"
      close-on-esc="false"
      close-on-overlay-click="false"
    >
      <mdui-icon slot="icon" name="error" style="color: rgb(var(--mdui-color-error));"></mdui-icon>
      <div class="dialog-content">
        <p class="dialog-description">{{ error }}</p>
      </div>
    </mdui-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import { getPaste, getPasteContent, type PasteData, type PasteFile } from '@/services/paste'
import { decryptContent, urlSafeStrToKey } from '@/utils/crypto'
import { useTheme } from '@/composables/useTheme'
import { useAuth } from '@/composables/useAuth'
import { useFavorites } from '@/composables/useFavorites'
import { loadGuestHistory } from '@/composables/useHistory'
import { getHistoryDetail } from '@/services/history'
import {
  registerHeaderActions,
  triggerHeaderActionFlash,
  unregisterHeaderActions
} from '@/composables/useHeaderActions'
import { formatDate } from '@/utils/format'
import PlainViewer from '@/components/viewers/Plain.vue'
import PasteFilesDialog from '@/components/paste/PasteFilesDialog.vue'
import 'mdui/components/circular-progress.js'
import 'mdui/components/card.js'
import 'mdui/components/dialog.js'
import 'mdui/components/text-field.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/top-app-bar.js'
import 'mdui/components/tooltip.js'
import '@mdui/icons/remove-red-eye.js'
import '@mdui/icons/create.js'
import '@mdui/icons/auto-delete.js'
import '@mdui/icons/code.js'
import '@mdui/icons/article.js'
import '@mdui/icons/folder.js'

useTheme()

const MarkdownViewer = defineAsyncComponent(() => import('@/components/viewers/Markdown.vue'))

const route = useRoute()
const router = useRouter()
const { currentUser } = useAuth()
const {
  addFavorite,
  removeFavorite,
  isFavorite,
  initFavoritesFromCache
} = useFavorites()
const HEADER_OWNER_ID = 'paste-viewer-page'
const VIEWER_FAVORITE_ACTION_ID = 'paste-viewer-favorite'
const VIEWER_EDIT_ACTION_ID = 'paste-viewer-edit'
const EDIT_CONTEXT_STORAGE_KEY = 'mb_editor_edit_context_v1'
const ADMIN_KEY_SESSION_PREFIX = 'mb_admin_key:'
// 房间共享打开新标签页时，通过 localStorage 短时交接 admin_key
const ADMIN_KEY_HANDOFF_PREFIX = 'mb_viewer_admin_key_handoff:'
const ADMIN_KEY_HANDOFF_TTL_MS = 60 * 1000

// 状态
const pasteData = ref<PasteData | null>(null)
const pasteFiles = ref<PasteFile[]>([])
const decryptedContent = ref<string>('')
const isLoading = ref<boolean>(true)
const error = ref<string>('')
const viewerType = ref<'txt' | 'md'>('txt')
const encryptionKeyBytes = ref<Uint8Array | null>(null)
const favoriteState = ref(false)
const favoriteBusy = ref(false)
const favoriteStateReady = ref(false)
let favoriteReminderFrame = 0

// Access Key 相关
const accessKeyDialog = ref<any>(null)
const accessKeyInput = ref<string>('')
const accessKeyError = ref<boolean>(false)
const currentAccessKey = ref<string | undefined>(undefined)

// 编辑权限：存在 admin_key 时在顶栏显示编辑按钮
const currentAdminKey = ref<string>('')

// 错误对话框
const errorDialog = ref<any>(null)
const pasteFilesDialog = ref<{ open: () => void } | null>(null)

const pasteTitle = computed(() => pasteData.value?.title || '未命名 Paste')
const pasteCreatedText = computed(() => {
  const v = pasteData.value?.published_at || pasteData.value?.updated_at
  return formatDate(v)
})
const pasteExpireInlineText = computed(() => {
  const v = pasteData.value?.expire_at ?? null
  if (!v) return '永不过期'
  return formatDate(v)
})
const pasteViewsText = computed(() => {
  const viewCount = Number(pasteData.value?.view_count)
  return Number.isFinite(viewCount) && viewCount >= 0 ? viewCount : 0
})
const pasteFilesText = computed(() => `${pasteFiles.value.length} 个文件`)
const pasteId = computed(() => String(route.params.paste_id || ''))
const encryptionKeyHash = computed(() => window.location.hash || '')

function currentUserId(): number | null {
  return currentUser.value?.id ?? null
}

function currentUrlEncryptionKey(): string {
  if (typeof window === 'undefined') return ''
  return window.location.hash.substring(1).trim()
}

function takeSharedAdminKeyHandoff(id: string): string {
  const storageKey = `${ADMIN_KEY_HANDOFF_PREFIX}${id}`
  try {
    const raw = localStorage.getItem(storageKey)
    if (!raw) return ''
    localStorage.removeItem(storageKey)
    const parsed = JSON.parse(raw) as { admin_key?: unknown; created_at?: unknown }
    const adminKey = typeof parsed.admin_key === 'string' ? parsed.admin_key.trim() : ''
    const createdAt = typeof parsed.created_at === 'number' ? parsed.created_at : 0
    if (!adminKey || Date.now() - createdAt > ADMIN_KEY_HANDOFF_TTL_MS) return ''
    return adminKey
  } catch {
    return ''
  }
}

/**
 * 解析当前 Paste 的 admin_key：
 * 房间共享交接 > 本标签页缓存 > 游客本地历史 > 登录用户历史
 */
async function resolveAdminKey(): Promise<void> {
  const id = pasteId.value
  if (!id) return

  const handoff = takeSharedAdminKeyHandoff(id)
  if (handoff) {
    currentAdminKey.value = handoff
    try {
      sessionStorage.setItem(`${ADMIN_KEY_SESSION_PREFIX}${id}`, handoff)
    } catch {
      // ignore
    }
    return
  }

  try {
    const cached = sessionStorage.getItem(`${ADMIN_KEY_SESSION_PREFIX}${id}`)?.trim()
    if (cached) {
      currentAdminKey.value = cached
      return
    }
  } catch {
    // ignore
  }

  const guestItem = loadGuestHistory().find((item) => item.pasteId === id)
  if (guestItem?.adminKey) {
    currentAdminKey.value = guestItem.adminKey
    return
  }

  if (!currentUser.value) return

  try {
    const detail = await getHistoryDetail(id)
    if (pasteId.value === id && detail.admin_key) {
      currentAdminKey.value = detail.admin_key
    }
  } catch {
    // 不在历史记录中，视为无编辑权限
  }
}

function openInEditor(): void {
  const id = pasteId.value
  const adminKey = currentAdminKey.value
  const encryptionKey = currentUrlEncryptionKey()
  if (!id || !adminKey || !encryptionKey) {
    snackbar({ message: '缺少编辑所需密钥', closeable: true })
    return
  }

  try {
    sessionStorage.setItem(
      EDIT_CONTEXT_STORAGE_KEY,
      JSON.stringify({
        paste_id: id,
        admin_key: adminKey,
        encryption_key: encryptionKey,
        created_at: Date.now()
      })
    )
  } catch {
    snackbar({ message: '浏览器存储不可用，无法进入编辑模式', closeable: true })
    return
  }

  void router.push({ path: '/', query: { edit: '1', paste_id: id } })
}

async function copyDecryptedContent(): Promise<void> {
  if (!decryptedContent.value) {
    snackbar({ message: '内容尚未加载', closeable: true })
    return
  }

  try {
    await navigator.clipboard.writeText(decryptedContent.value)
    snackbar({ message: 'Paste 内容已复制' })
  } catch {
    snackbar({ message: '复制失败，请手动复制', closeable: true })
  }
}

async function syncFavoriteState(): Promise<void> {
  const id = pasteId.value
  if (!id) {
    favoriteState.value = false
    favoriteStateReady.value = true
    return
  }

  favoriteStateReady.value = false
  favoriteState.value = await isFavorite(id, currentUserId())
  favoriteStateReady.value = true
}

async function toggleFavorite(): Promise<void> {
  const id = pasteId.value
  if (!id || favoriteBusy.value) return

  favoriteBusy.value = true
  try {
    if (favoriteState.value) {
      await removeFavorite(id, currentUserId())
      favoriteState.value = false
      snackbar({ message: '已取消收藏' })
      return
    }

    const key = currentUrlEncryptionKey()
    if (!key) {
      snackbar({ message: '缺少解密密钥，无法收藏', closeable: true })
      return
    }

    await addFavorite(id, key, currentUserId(), {
      title: pasteTitle.value,
      status: pasteData.value?.status === 'edited' ? 'edited' : 'published',
      accessKey: currentAccessKey.value
    })
    favoriteState.value = true
    snackbar({ message: '已收藏' })
  } catch {
    snackbar({ message: favoriteState.value ? '取消收藏失败' : '收藏失败', closeable: true })
  } finally {
    favoriteBusy.value = false
  }
}

function favoriteReminderKey(): string {
  return `mb_favorite_reminded_${pasteId.value}`
}

function hasFavoriteReminderBeenShown(): boolean {
  if (typeof window === 'undefined' || !pasteId.value) return true
  try {
    return sessionStorage.getItem(favoriteReminderKey()) === '1'
  } catch {
    return true
  }
}

function markFavoriteReminderShown(): void {
  if (typeof window === 'undefined' || !pasteId.value) return
  try {
    sessionStorage.setItem(favoriteReminderKey(), '1')
  } catch {
    // ignore unavailable storage
  }
}

function isNearPageBottom(): boolean {
  if (typeof window === 'undefined') return false
  const scrollTop = window.scrollY || document.documentElement.scrollTop || 0
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0
  const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight || 0
  return scrollTop + viewportHeight >= scrollHeight - 240
}

function maybeTriggerFavoriteReminder(): void {
  if (!favoriteStateReady.value) return
  if (!pasteData.value || !decryptedContent.value) return
  if (favoriteState.value || hasFavoriteReminderBeenShown()) return
  if (!isNearPageBottom()) return

  markFavoriteReminderShown()
  triggerHeaderActionFlash(VIEWER_FAVORITE_ACTION_ID)
}

function scheduleFavoriteReminderCheck(): void {
  if (typeof window === 'undefined' || favoriteReminderFrame) return
  favoriteReminderFrame = window.requestAnimationFrame(() => {
    favoriteReminderFrame = 0
    maybeTriggerFavoriteReminder()
  })
}

function handleScrollForFavoriteReminder(): void {
  scheduleFavoriteReminderCheck()
}

function openPasteFilesDialog() {
  pasteFilesDialog.value?.open()
}

/**
 * 显示错误对话框
 */
function showErrorDialog(errorMessage: string) {
  error.value = errorMessage
  if (errorDialog.value) {
    errorDialog.value.open = true
  }
}

/**
 * 验证必需参数
 */
function validateParams(): { pasteId: string; encryptionKey: Uint8Array } | null {
  const pasteId = route.params.paste_id as string
  if (!pasteId) {
    showErrorDialog('URL 中缺少 Paste ID。')
    return null
  }

  const encryptionKeyStr = window.location.hash.substring(1)
  if (!encryptionKeyStr) {
    showErrorDialog('URL 中缺少加密密钥（hash 部分）。')
    return null
  }

  try {
    const encryptionKey = urlSafeStrToKey(encryptionKeyStr)
    encryptionKeyBytes.value = encryptionKey
    return { pasteId, encryptionKey }
  } catch (err) {
    showErrorDialog('无效的加密密钥格式。')
    return null
  }
}

/**
 * 切换 Viewer 类型
 */
function toggleViewerType() {
  viewerType.value = viewerType.value === 'md' ? 'txt' : 'md'
}

/**
 * 加载 Paste 数据
 */
async function loadPaste(pasteId: string, encryptionKey: Uint8Array, accessKey?: string): Promise<boolean> {
  try {
    pasteFiles.value = []
    const [data, content] = await Promise.all([
      getPaste(pasteId, accessKey),
      getPasteContent(pasteId, accessKey)
    ])

    if (!content.encrypted_content) {
      throw new Error('内容为空或格式不正确')
    }

    pasteData.value = data
    pasteFiles.value = Array.isArray(content.files) ? content.files : []
    decryptedContent.value = await decryptContent(content.encrypted_content, encryptionKey)
    currentAccessKey.value = accessKey
    if (accessKey && accessKey.trim()) {
      try {
        sessionStorage.setItem(`mb_access_key:${pasteId}`, accessKey.trim())
      } catch {
        // ignore
      }
    }
    
    // 根据 paste 类型设置默认 viewer（不使用持久化）
    viewerType.value = data.type === 'md' ? 'md' : 'txt'

    void resolveAdminKey()

    return true
  } catch (e: any) {
    return handleLoadError(e)
  }
}

/**
 * 处理加载错误
 */
function handleLoadError(e: any): boolean {
  if (e.response) {
    const status = e.response.status
    
    if (status === 404) {
      showErrorDialog('Paste 不存在，这可能是因为 Paste ID 错误或 Paste 已被删除。')
    } else if (status === 403) {
      // 需要 access key - 返回特殊标记
      return false // 不设置错误，由调用方处理
    } else {
      showErrorDialog(`服务器错误 (${status})：${e.response.data?.message || '未知错误'}`)
    }
  } else if (e instanceof Error) {
    if (e.message.includes('decrypt') || e.name === 'OperationError') {
      showErrorDialog('解密失败，密钥可能不正确或数据已损坏。')
    } else {
      showErrorDialog(`发生错误：${e.message}`)
    }
  } else {
    showErrorDialog('发生未知错误。')
  }
  
  console.error('Load paste error:', e)
  return false
}

/**
 * 显示 Access Key 输入对话框
 */
function showAccessKeyDialog(isRetry: boolean = false) {
  isLoading.value = false
  // 重试时清空输入但保持错误状态；首次显示时清空两者
  accessKeyInput.value = ''
  if (!isRetry) {
    accessKeyError.value = false
  }
  if (accessKeyDialog.value) {
    accessKeyDialog.value.open = true
  }
}

/**
 * 处理 Access Key 提交
 */
async function handleAccessKeySubmit() {
  const params = validateParams()
  if (!params) return

  const trimmedKey = accessKeyInput.value.trim()
  if (!trimmedKey) {
    accessKeyError.value = true
    return
  }

  // 关闭对话框并重新加载
  if (accessKeyDialog.value) {
    accessKeyDialog.value.open = false
  }
  isLoading.value = true
  error.value = ''
  currentAccessKey.value = trimmedKey

  const success = await loadPaste(params.pasteId, params.encryptionKey, trimmedKey)
  if (success) {
    await syncFavoriteState()
  } else {
    favoriteStateReady.value = true
  }
   
  if (!success && !error.value) {
    // 如果失败且没有其他错误（即 403），说明密钥错误
    accessKeyError.value = true
    showAccessKeyDialog(true) // 传入 true 表示是重试，不清除输入和错误状态
  }
  
  isLoading.value = false
}

/**
 * 初始化加载
 */
onMounted(async () => {
  registerHeaderActions(HEADER_OWNER_ID, [
    {
      id: VIEWER_EDIT_ACTION_ID,
      label: '编辑',
      ariaLabel: '编辑此 Paste',
      icon: 'edit',
      kind: 'icon',
      visible: () => !!currentAdminKey.value && !!pasteData.value,
      onClick: openInEditor
    },
    {
      id: 'paste-viewer-copy',
      label: '复制内容',
      ariaLabel: '复制 Paste 内容',
      icon: 'content_copy',
      kind: 'icon',
      disabled: () => isLoading.value || !decryptedContent.value,
      onClick: copyDecryptedContent
    },
    {
      id: 'paste-viewer-new-paste',
      label: '新建 Paste',
      ariaLabel: '新建 Paste',
      icon: 'add',
      kind: 'icon',
      onClick: () => { void router.push('/') }
    },
    {
      id: VIEWER_FAVORITE_ACTION_ID,
      label: () => (favoriteState.value ? '取消收藏' : '收藏'),
      ariaLabel: () => (favoriteState.value ? '取消收藏此 Paste' : '收藏此 Paste'),
      icon: () => (favoriteState.value ? 'star' : 'star_border'),
      kind: 'icon',
      active: () => favoriteState.value,
      disabled: () => favoriteBusy.value || !pasteId.value,
      onClick: toggleFavorite
    }
  ])

  if (currentUser.value) {
    initFavoritesFromCache(currentUser.value.id)
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('scroll', handleScrollForFavoriteReminder, { passive: true })
  }

  isLoading.value = true
  error.value = ''

  const params = validateParams()
  if (!params) {
    isLoading.value = false
    favoriteStateReady.value = true
    return
  }

  let cachedAccessKey: string | undefined = undefined
  try {
    const cached = sessionStorage.getItem(`mb_access_key:${params.pasteId}`)
    if (cached && cached.trim()) cachedAccessKey = cached.trim()
  } catch {
    // ignore
  }

  const success = await loadPaste(params.pasteId, params.encryptionKey, cachedAccessKey)
  if (success) {
    await syncFavoriteState()
  } else {
    favoriteStateReady.value = true
  }
   
  if (!success && !error.value) {
    // 首次加载时需要 access key
    showAccessKeyDialog(false)
  }
   
  isLoading.value = false
})

watch(
  () => currentUser.value?.id ?? null,
  (userId) => {
    if (userId !== null) {
      initFavoritesFromCache(userId)
    }
    void syncFavoriteState()
    if (pasteData.value && !currentAdminKey.value) {
      void resolveAdminKey()
    }
  }
)

onBeforeUnmount(() => {
  unregisterHeaderActions(HEADER_OWNER_ID)
  if (typeof window !== 'undefined') {
    window.removeEventListener('scroll', handleScrollForFavoriteReminder)
    if (favoriteReminderFrame) {
      window.cancelAnimationFrame(favoriteReminderFrame)
      favoriteReminderFrame = 0
    }
  }
})
</script>

<style scoped>
.paste-view {
  padding-top: 0rem;
  padding-bottom: 1rem;
}

.loading-indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.paste-content {
  margin-top: 1rem;
}

.paste-header {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin-bottom: 4px;
}

.paste-title {
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 2rem;
  line-height: 1.25;
  font-weight: 700;
}

.paste-header mdui-tooltip {
  display: inline-flex;
  flex: 0 0 auto;
}

.paste-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 0;
  margin-bottom: 20px;
  font-size: 13px;
  color: rgb(var(--mdui-color-outline));
}

.paste-meta mdui-tooltip::after {
  content: '';
  margin: 0 8px;
  opacity: 0.5;
}

.paste-meta mdui-tooltip:last-child::after {
  display: none;
}

.paste-meta .meta-icon {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.paste-meta .meta-icon :is(mdui-icon-remove-red-eye, mdui-icon-create, mdui-icon-auto-delete, mdui-icon-folder) {
  font-size: 15px;
}

.paste-meta .meta-action {
  border: 0;
  background: transparent;
  margin: 0;
  padding: 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.paste-meta .meta-action:hover {
  color: rgb(var(--mdui-color-primary));
}

.paste-meta .meta-action:focus-visible {
  outline: 2px solid rgb(var(--mdui-color-primary));
  outline-offset: 2px;
  border-radius: 4px;
}

/* Dialog 样式 */
.dialog-content {
  padding: 16px 0;
}

.dialog-description {
  font-size: 14px;
  color: rgb(var(--mdui-color-on-surface-variant));
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
