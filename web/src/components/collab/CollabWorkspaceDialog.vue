<template>
  <mdui-dialog
    ref="dialogRef"
    class="collab-workspace-dialog"
    close-on-esc
    close-on-overlay-click
    @closed="handleDialogClosed"
  >
    <div class="dialog-shell">
      <section class="room-sheet">
        <header class="sheet-header">
          <h2>房间 {{ activeRoomSession?.pinCode || '—' }}</h2>
          <h3 class="sheet-subtitle">
            <span>{{ activeRoomSession?.memberCount ?? '—' }}/{{ activeRoomSession?.maxMembers ?? '—' }}人</span>
            <span class="sheet-subtitle-separator" aria-hidden="true">·</span>
            <span>你是 {{ memberIdentity?.displayName || '—' }}</span>
          </h3>
        </header>

        <mdui-tabs
          class="workspace-tabs"
          variant="secondary"
          full-width
          :value="activeTab"
          @change="handleTabChange"
        >
          <mdui-tab value="shareable">可共享</mdui-tab>
          <mdui-tab value="shared">已共享</mdui-tab>

          <mdui-tab-panel slot="panel" value="shareable">
            <div class="tab-panel">
              <section class="panel-card source-panel" :aria-busy="isSharing ? 'true' : 'false'">
                <div class="panel-copy">
                  <h4>选择要分享的 Paste</h4>
                  <p>先选内容，再把它发送给房间里的成员。</p>
                </div>

                <div class="source-stack">
                  <div
                    v-if="hasCurrentShareSource"
                    class="source-card"
                    :class="{ active: selectedShareSource === 'current' }"
                    @click="handleSelectSource('current')"
                  >
                    <div class="source-card-main">
                      <span class="source-label">刚刚创建的 Paste</span>
                      <strong>{{ currentShareTitle }}</strong>
                    </div>
                    <label class="inline-edit-switch" @click.stop>
                      <span>启用编辑</span>
                      <mdui-switch :checked="shareCurrentWithEdit" @change="handleCurrentEditSwitchChange"></mdui-switch>
                    </label>
                  </div>

                  <div class="source-shortcuts">
                    <mdui-button
                      variant="tonal"
                      class="manual-toggle"
                      :class="{ active: selectedShareSource === 'history' }"
                      @click="handleOpenHistoryPicker"
                    >
                      选择历史 Paste
                    </mdui-button>

                    <mdui-button
                      variant="tonal"
                      class="manual-toggle"
                      :class="{ active: manualInputExpanded }"
                      @click="handleToggleManualInput"
                    >
                      {{ manualInputExpanded ? '收起手动输入' : '手动输入' }}
                    </mdui-button>
                  </div>

                  <div
                    v-if="selectedHistoryItem"
                    class="source-card"
                    :class="{ active: selectedShareSource === 'history' }"
                    @click="handleSelectSource('history')"
                  >
                    <div class="source-card-main">
                      <span class="source-label">历史 Paste</span>
                      <strong>{{ selectedHistoryTitle }}</strong>
                      <p>{{ selectedHistoryDescription }}</p>
                    </div>
                    <label class="inline-edit-switch" @click.stop>
                      <span>启用编辑</span>
                      <mdui-switch :checked="shareHistoryWithEdit" @change="handleHistoryEditSwitchChange"></mdui-switch>
                    </label>
                  </div>

                  <div v-if="manualInputExpanded" class="source-body manual-body">
                    <mdui-text-field
                      label="Paste 链接或 ID"
                      placeholder="例如 /p/AbCd1234#key 或 AbCd1234"
                      variant="outlined"
                      :value="manualShareInput"
                      @input="handleManualShareInput"
                    ></mdui-text-field>

                    <label class="edit-switch-row">
                      <span>启用编辑</span>
                      <mdui-switch :checked="shareManualWithEdit" @change="handleManualEditSwitchChange"></mdui-switch>
                    </label>

                    <p
                      class="source-hint"
                      :class="{ 'source-hint-error': !!manualShareError }"
                      :role="manualShareError ? 'alert' : undefined"
                      :aria-live="manualShareError ? 'polite' : undefined"
                    >
                      {{ manualShareError || manualShareHint }}
                    </p>
                  </div>
                </div>

                <p v-if="shareStatusCopy" class="share-status">{{ shareStatusCopy }}</p>
              </section>

              <section class="panel-card target-panel" :aria-busy="isMembersLoading ? 'true' : 'false'">
                <div class="panel-copy">
                  <h4>选择分享对象</h4>
                </div>

                <div class="target-strip">
                  <button
                    type="button"
                    class="target-pill target-pill-broadcast"
                    :class="{ active: !shareTargetMemberId }"
                    @click="handleBroadcastTarget"
                  >
                    @全体
                  </button>
                  <button
                    v-for="member in targetableMembers"
                    :key="member.member_id"
                    type="button"
                    class="target-pill"
                    :class="{ active: shareTargetMemberId === member.member_id }"
                    :data-online="member.is_online ? 'true' : 'false'"
                    @click="handleSelectShareTarget(member.member_id)"
                  >
                    @{{ member.display_name }}{{ member.is_online ? '' : ' [离线]' }}
                  </button>
                </div>

                <mdui-button
                  variant="filled"
                  :disabled="!canShareSelectedSource"
                  :loading="isSharing"
                  @click="handleShareSelectedSource"
                >
                  {{ shareActionLabel }}
                </mdui-button>
              </section>
            </div>
          </mdui-tab-panel>

          <mdui-tab-panel slot="panel" value="shared">
            <div class="tab-panel shared-tab-panel">
              <section class="panel-card paste-panel" :aria-busy="isPastesLoading ? 'true' : 'false'">
                <div class="panel-head">
                  <div class="panel-copy">
                    <h4>已共享内容</h4>
                  </div>
                </div>

                <div class="paste-panel-body">
                  <div v-if="pastes.length === 0 && !isPastesLoading" class="empty-block">
                    还没有共享内容，发出第一条 Paste 吧。
                  </div>

                  <div v-else class="paste-list">
                    <article
                      v-for="paste in pastes"
                      :key="`${paste.paste_id}-${paste.shared_at}`"
                      class="paste-card"
                      :class="{ unread: isUnreadPaste(paste) }"
                    >
                      <div class="paste-main">
                        <div>
                          <h5>{{ paste.title || paste.paste_id }}</h5>
                          <p>
                            来自 {{ memberName(paste.shared_by) }}
                            <template v-if="paste.target_member"> · 发给 {{ memberName(paste.target_member) }}</template>
                          </p>
                        </div>
                      </div>

                      <div class="paste-meta">
                        <span>{{ formatDateTime(paste.shared_at) }}</span>
                        <span v-if="paste.expire_at">将于 {{ formatDateTime(paste.expire_at) }}过期</span>
                      </div>

                      <div class="paste-actions">
                        <mdui-button
                          :variant="isUnreadPaste(paste) ? 'filled' : 'tonal'"
                          :disabled="paste.is_expired"
                          @click="handleOpenSharedPaste(paste)"
                        >
                          打开
                        </mdui-button>
                        <mdui-button
                          v-if="paste.encrypted_admin_key"
                          :variant="isUnreadPaste(paste) ? 'filled' : 'tonal'"
                          :disabled="paste.is_expired"
                          @click="handleEditSharedPaste(paste)"
                        >
                          编辑
                        </mdui-button>
                        <mdui-button variant="text" @click="handleCopyPasteLink(paste)">复制</mdui-button>
                      </div>
                    </article>
                  </div>
                </div>
              </section>
            </div>
          </mdui-tab-panel>
        </mdui-tabs>
      </section>

      <footer class="dialog-actions">
        <mdui-button class="leave-button" variant="filled" :loading="isLeaving" @click="handleLeaveRoom">离开</mdui-button>
        <mdui-button variant="text" :disabled="isLeaving" @click="closeWorkspaceDialog">关闭</mdui-button>
      </footer>
    </div>
  </mdui-dialog>

  <mdui-dialog
    ref="historyDialogRef"
    class="history-picker-dialog"
    close-on-esc
    close-on-overlay-click
    @closed="closeHistoryPicker"
  >
    <div class="dialog-shell">
      <section class="room-sheet">
        <header class="sheet-header">
          <h2>选择历史 Paste</h2>
          <h3>{{ historyPickerSummary }}</h3>
        </header>

        <div class="history-picker-body">
          <div v-if="historyPickerItems.length === 0 && !isHistoryPickerLoading" class="empty-block">
            还没有可选择的历史 Paste。
          </div>

          <div v-else class="history-picker-list" :aria-busy="isHistoryPickerLoading ? 'true' : 'false'">
            <button
              v-for="item in historyPickerItems"
              :key="item.pasteId"
              type="button"
              class="history-picker-item"
              :class="{ active: selectedHistoryPasteId === item.pasteId }"
              @click="handleSelectHistoryPaste(item.pasteId)"
            >
              <div class="history-picker-copy">
                <strong>{{ item.title || item.pasteId }}</strong>
                <p>{{ item.pasteId }}</p>
              </div>
              <div class="history-picker-meta">
                <span>{{ formatDateTime(item.updatedAt) }}</span>
                <span v-if="item.expireAt">将于 {{ formatDateTime(item.expireAt) }}过期</span>
              </div>
            </button>
          </div>
        </div>
      </section>

      <footer class="dialog-actions history-dialog-actions">
        <mdui-button variant="text" @click="closeHistoryPicker">关闭</mdui-button>
      </footer>
    </div>
  </mdui-dialog>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import 'mdui/components/button.js'
import 'mdui/components/dialog.js'
import 'mdui/components/switch.js'
import 'mdui/components/tab-panel.js'
import 'mdui/components/tab.js'
import 'mdui/components/tabs.js'
import 'mdui/components/text-field.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import { useAuth } from '../../composables/useAuth'
import { useCollabDialogState } from '../../composables/useCollabDialogState'
import { buildUnreadPasteKey, useCollabUnreadPastes } from '../../composables/useCollabUnreadPastes'
import { loadGuestHistory } from '../../composables/useHistory'
import { useRoomRealtime, type RoomRealtimeEvent } from '../../composables/useRoomRealtime'
import { useRoomSession } from '../../composables/useRoomSession'
import { getHistory, getHistoryDetail, type HistoryListItem } from '../../services/history'
import {
  getRoomInfoByPin,
  getRoomMembers,
  getRoomPastes,
  sharePasteToRoom,
  type RoomMember,
  type SharedPasteRecord
} from '../../services/rooms'
import { buildAbsoluteAppUrl } from '../../utils/appUrl'
import { bytesToStr, decryptWithKey, encryptWithKey, keyToUrlSafeStr, strToBytes, urlSafeStrToKey } from '../../utils/crypto'

type DialogElement = HTMLElement & { open: boolean }
type WorkspaceTab = 'shareable' | 'shared'
type ShareSource = 'current' | 'manual' | 'history'

interface HistoryPickerItem {
  pasteId: string
  title: string | null
  updatedAt: string
  expireAt: string | null
}

const EDIT_CONTEXT_STORAGE_KEY = 'mb_editor_edit_context_v1'

const props = defineProps<{
  currentPasteId: string
  currentAdminKey: string
  currentPasteTitle: string
  currentPasteUrl: string
  encryptionKey: string
}>()

const emit = defineEmits<{
  sharedCurrentPaste: []
}>()

const dialogRef = ref<DialogElement | null>(null)
const historyDialogRef = ref<DialogElement | null>(null)
const members = ref<RoomMember[]>([])
const pastes = ref<SharedPasteRecord[]>([])
const historyPickerItems = ref<HistoryPickerItem[]>([])
const isMembersLoading = ref(false)
const isPastesLoading = ref(false)
const isHistoryPickerLoading = ref(false)
const isSharing = ref(false)
const isLeaving = ref(false)
const isHistoryPickerOpen = ref(false)
const isResolvingMissingRoom = ref(false)
const shareTargetMemberId = ref<string | null>(null)
const activeTab = ref<WorkspaceTab>('shareable')
const viewedUnreadPasteKeys = ref<string[]>([])
const selectedShareSource = ref<ShareSource>('current')
const selectedHistoryPasteId = ref('')
const manualInputExpanded = ref(false)
const shareCurrentWithEdit = ref(true)
const shareHistoryWithEdit = ref(true)
const shareManualWithEdit = ref(false)
const manualShareInput = ref('')
const manualShareError = ref('')

const { currentUser } = useAuth()
const { isWorkspaceDialogOpen, workspaceDialogIntent, closeWorkspaceDialog } = useCollabDialogState()
const { activeRoom, memberIdentity, roomKeyBytes, syncRoomInfo, leaveActiveRoom, clearActiveRoom } = useRoomSession()
const { selfMemberId, connect, disconnect } = useRoomRealtime()
const { hasUnreadPastes, useRoomUnreadKeys, clearUnreadPastes, clearRoomUnreadState, markUnreadPaste } = useCollabUnreadPastes()
const router = useRouter()

const activeRoomSession = computed(() => activeRoom.value)
const activeRoomId = computed(() => activeRoomSession.value?.roomId ?? '')
const unreadPasteKeys = useRoomUnreadKeys(activeRoomId)
const targetableMembers = computed(() => members.value.filter((member) => member.member_id !== selfMemberId.value))
const hasOtherMembers = computed(() => targetableMembers.value.length > 0)
const currentShareUnavailable = computed(() => !props.currentPasteId || !props.encryptionKey)
const hasCurrentShareSource = computed(() => !currentShareUnavailable.value)
const currentShareTitle = computed(() => props.currentPasteTitle || props.currentPasteId || '尚未生成可共享的 Paste')
const selectedHistoryItem = computed(() =>
  historyPickerItems.value.find((item) => item.pasteId === selectedHistoryPasteId.value) ?? null
)
const selectedHistoryTitle = computed(
  () => selectedHistoryItem.value?.title || selectedHistoryItem.value?.pasteId || '未命名的历史 Paste'
)
const selectedHistoryDescription = computed(() => {
  const item = selectedHistoryItem.value
  if (!item) return ''
  return item.expireAt ? `将于 ${formatDateTime(item.expireAt)}过期` : `更新于 ${formatDateTime(item.updatedAt)}`
})
const historyPickerSummary = computed(() => {
  if (isHistoryPickerLoading.value) return '正在加载'
  if (historyPickerItems.value.length === 0) return '暂无内容'
  return `${historyPickerItems.value.length}条记录`
})
const manualShareHint = computed(() =>
  shareManualWithEdit.value
    ? '若要启用编辑，会优先从当前编辑器或本地历史中查找管理密钥。'
    : '粘贴 Paste 链接，或直接输入 Paste ID。'
)
const shareActionLabel = computed(() => (shareTargetMemberId.value ? '发送给此成员' : '发送给全体'))
const canShareSelectedSource = computed(() => {
  if (!activeRoomSession.value || !memberIdentity.value || !roomKeyBytes.value || !hasOtherMembers.value || isSharing.value) {
    return false
  }

  if (selectedShareSource.value === 'current') {
    return !currentShareUnavailable.value
  }

  if (selectedShareSource.value === 'history') {
    return Boolean(selectedHistoryPasteId.value)
  }

  if (!manualInputExpanded.value) {
    return false
  }

  return manualShareInput.value.trim().length > 0
})
const shareStatusCopy = computed(() => {
  if (!hasOtherMembers.value) return ''
  if (selectedShareSource.value === 'current') {
    return currentShareUnavailable.value ? '请先提交并发布当前内容，再把它共享给房间成员。' : ''
  }
  if (selectedShareSource.value === 'history') {
    return ''
  }
  if (!manualInputExpanded.value) {
    return hasCurrentShareSource.value
      ? '也可以选择历史 Paste，或点击“手动输入”分享任意已存在的 Paste。'
      : '你可以选择历史 Paste，或点击“手动输入”粘贴任意 Paste 链接或 ID。'
  }
  return manualShareError.value || '你可以粘贴任意 Paste 链接，快速转发给房间成员。'
})

interface ResolvedShareSource {
  pasteId: string
  encryptionKey: string
  adminKey: string
  shareWithEdit: boolean
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim()) return error.message
  return fallback
}

function memberName(memberId: string | null): string {
  if (!memberId) return '所有成员'
  if (memberId === selfMemberId.value) return '你'
  const member = members.value.find((entry) => entry.member_id === memberId)
  return member?.display_name || memberId
}

function formatDateTime(value: string): string {
  const parsed = new Date(/(Z|[+\-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`)
  if (Number.isNaN(parsed.getTime())) return '-'
  return parsed.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function eventValue(event: Event): string {
  const target = event.target as HTMLInputElement | { value?: unknown } | null
  const value = target && 'value' in target ? target.value : ''
  return typeof value === 'string' ? value : value == null ? '' : String(value)
}

function eventChecked(event: Event): boolean {
  const target = event.target as HTMLInputElement | { checked?: unknown } | null
  return Boolean(target && 'checked' in target ? target.checked : false)
}

function handleTabChange(event: Event): void {
  const value = eventValue(event)
  activeTab.value = value === 'shared' ? 'shared' : 'shareable'
  if (activeTab.value === 'shared') {
    rememberVisibleUnreadPastes()
  }
}

function handleCurrentEditSwitchChange(event: Event): void {
  shareCurrentWithEdit.value = eventChecked(event)
}

function handleHistoryEditSwitchChange(event: Event): void {
  shareHistoryWithEdit.value = eventChecked(event)
}

function handleManualEditSwitchChange(event: Event): void {
  shareManualWithEdit.value = eventChecked(event)
  manualShareError.value = ''
}

function handleManualShareInput(event: Event): void {
  if (!manualInputExpanded.value) {
    manualInputExpanded.value = true
  }
  selectedShareSource.value = 'manual'
  manualShareInput.value = eventValue(event)
  manualShareError.value = ''
}

function handleSelectSource(source: ShareSource): void {
  if (source === 'current' && currentShareUnavailable.value) return
  if (source === 'history' && !selectedHistoryItem.value) return
  selectedShareSource.value = source
  if (source === 'manual') {
    manualInputExpanded.value = true
  } else {
    manualInputExpanded.value = false
  }
  manualShareError.value = ''
}

function handleToggleManualInput(): void {
  if (manualInputExpanded.value) {
    manualInputExpanded.value = false
    if (hasCurrentShareSource.value) {
      selectedShareSource.value = 'current'
    } else if (selectedHistoryItem.value) {
      selectedShareSource.value = 'history'
    }
    manualShareError.value = ''
    return
  }

  manualInputExpanded.value = true
  selectedShareSource.value = 'manual'
  manualShareError.value = ''
}

function sharedPasteEntryKey(paste: SharedPasteRecord): string {
  return buildUnreadPasteKey(paste.paste_id, paste.shared_at)
}

function isUnreadPaste(paste: SharedPasteRecord): boolean {
  return unreadPasteKeys.value.includes(sharedPasteEntryKey(paste))
}

function rememberVisibleUnreadPastes(): void {
  if (activeTab.value !== 'shared') return

  const visibleUnreadKeys = pastes.value.map(sharedPasteEntryKey).filter((key) => unreadPasteKeys.value.includes(key))
  if (!visibleUnreadKeys.length) return

  viewedUnreadPasteKeys.value = Array.from(new Set([...viewedUnreadPasteKeys.value, ...visibleUnreadKeys]))
}

function commitViewedUnreadPastes(): void {
  const roomId = activeRoomSession.value?.roomId
  if (!roomId || !viewedUnreadPasteKeys.value.length) {
    viewedUnreadPasteKeys.value = []
    return
  }

  clearUnreadPastes(roomId, viewedUnreadPasteKeys.value)
  viewedUnreadPasteKeys.value = []
}

function resolveWorkspaceTab(intent: 'overview' | 'share'): WorkspaceTab {
  if (intent === 'share') return 'shareable'
  return hasUnreadPastes(activeRoomSession.value?.roomId) ? 'shared' : 'shareable'
}

function toHistoryPickerItem(item: HistoryListItem): HistoryPickerItem {
  return {
    pasteId: item.paste_id,
    title: item.title,
    updatedAt: item.history_updated_at || item.paste_updated_at || item.published_at || new Date().toISOString(),
    expireAt: item.expire_at
  }
}

async function loadHistoryPickerItems(): Promise<void> {
  isHistoryPickerLoading.value = true
  try {
    if (!currentUser.value) {
      historyPickerItems.value = loadGuestHistory()
        .filter((item) => !item.isDeleted)
        .sort((a, b) => b.localCreatedAt - a.localCreatedAt)
        .map((item) => ({
          pasteId: item.pasteId,
          title: item.title || null,
          updatedAt: new Date(item.localCreatedAt).toISOString(),
          expireAt: null
        }))
      return
    }

    const response = await getHistory({ page: 1, limit: 50 })
    historyPickerItems.value = response.items.map(toHistoryPickerItem)
  } catch (error) {
    snackbar({
      message: extractErrorMessage(error, '加载历史 Paste 失败'),
      closeable: true
    })
  } finally {
    isHistoryPickerLoading.value = false
  }
}

async function handleOpenHistoryPicker(): Promise<void> {
  isHistoryPickerOpen.value = true
  await loadHistoryPickerItems()
}

function closeHistoryPicker(): void {
  isHistoryPickerOpen.value = false
}

function handleSelectHistoryPaste(pasteId: string): void {
  selectedHistoryPasteId.value = pasteId
  selectedShareSource.value = 'history'
  manualInputExpanded.value = false
  manualShareError.value = ''
  closeHistoryPicker()
}

function parsePasteReference(raw: string): { pasteId: string; encryptionKey: string } | null {
  const trimmed = raw.trim()
  if (!trimmed) return null

  const directId = trimmed.match(/^[A-Za-z0-9_-]{1,32}$/)
  if (directId) {
    return { pasteId: directId[0], encryptionKey: '' }
  }

  const relativeMatch = trimmed.match(/\/p\/([^/?#]+)(?:[?#].*)?$/)
  if (relativeMatch) {
    const pasteId = relativeMatch[1]?.trim()
    const hashMatch = trimmed.match(/#([^#\s]+)$/)
    return pasteId ? { pasteId, encryptionKey: hashMatch?.[1]?.trim() || '' } : null
  }

  if (typeof window !== 'undefined') {
    try {
      const url = new URL(trimmed, window.location.origin)
      const pathMatch = url.pathname.match(/\/p\/([^/?#]+)/)
      const pasteId = pathMatch?.[1]?.trim()
      if (!pasteId) return null
      return {
        pasteId,
        encryptionKey: url.hash.replace(/^#/, '').trim()
      }
    } catch {
      return null
    }
  }

  return null
}

function isRoomMissingError(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404
}

function resolveMissingRoom(options: { notify?: boolean } = {}): void {
  if (isResolvingMissingRoom.value) return

  isResolvingMissingRoom.value = true
  clearActiveRoom()
  disconnect()
  closeWorkspaceDialog()
  members.value = []
  pastes.value = []
  viewedUnreadPasteKeys.value = []

  if (options.notify !== false) {
    snackbar({ message: '房间已不存在，已离开当前房间', closeable: true })
  }
}

async function resolveLocalPasteSecrets(pasteId: string): Promise<{ encryptionKey: string; adminKey: string; title?: string | null }> {
  if (props.currentPasteId === pasteId) {
    return {
      encryptionKey: props.encryptionKey.trim(),
      adminKey: props.currentAdminKey.trim(),
      title: props.currentPasteTitle || null
    }
  }

  const guestItem = loadGuestHistory().find((item) => item.pasteId === pasteId)
  if (guestItem) {
    return {
      encryptionKey: guestItem.encryptionKey,
      adminKey: guestItem.adminKey,
      title: guestItem.title || null
    }
  }

  if (currentUser.value) {
    const detail = await getHistoryDetail(pasteId)
    return {
      encryptionKey: detail.encryption_key,
      adminKey: detail.admin_key,
      title: detail.title
    }
  }

  return {
    encryptionKey: '',
    adminKey: '',
    title: null
  }
}

async function resolveSelectedShareSource(): Promise<ResolvedShareSource> {
  if (selectedShareSource.value === 'current') {
    if (!props.currentPasteId || !props.encryptionKey) {
      throw new Error('当前还没有可共享的 Paste')
    }
    if (shareCurrentWithEdit.value && !props.currentAdminKey.trim()) {
      throw new Error('当前 Paste 缺少管理密钥，无法启用编辑共享')
    }
    return {
      pasteId: props.currentPasteId,
      encryptionKey: props.encryptionKey,
      adminKey: shareCurrentWithEdit.value ? props.currentAdminKey.trim() : '',
      shareWithEdit: shareCurrentWithEdit.value
    }
  }

  if (selectedShareSource.value === 'history') {
    const selected = selectedHistoryItem.value
    if (!selected) {
      throw new Error('请先选择一个历史 Paste')
    }

    const resolved = await resolveLocalPasteSecrets(selected.pasteId)
    if (!resolved.encryptionKey) {
      throw new Error('缺少该 Paste 的加密密钥，无法分享到房间')
    }

    if (shareHistoryWithEdit.value && !resolved.adminKey) {
      throw new Error('找不到该 Paste 的管理密钥，无法启用编辑共享')
    }

    return {
      pasteId: selected.pasteId,
      encryptionKey: resolved.encryptionKey,
      adminKey: shareHistoryWithEdit.value ? resolved.adminKey : '',
      shareWithEdit: shareHistoryWithEdit.value
    }
  }

  const parsed = parsePasteReference(manualShareInput.value)
  if (!parsed?.pasteId) {
    throw new Error('请输入有效的 Paste 链接或 Paste ID')
  }

  // Full share links already carry the paste key, so read-only forwarding should
  // not depend on the sender having saved this paste in their own history.
  if (!shareManualWithEdit.value && parsed.encryptionKey) {
    return {
      pasteId: parsed.pasteId,
      encryptionKey: parsed.encryptionKey,
      adminKey: '',
      shareWithEdit: false
    }
  }

  const resolved = await resolveLocalPasteSecrets(parsed.pasteId)
  const encryptionKey = parsed.encryptionKey || resolved.encryptionKey
  if (!encryptionKey) {
    throw new Error('缺少该 Paste 的加密密钥，无法分享到房间')
  }

  if (shareManualWithEdit.value && !resolved.adminKey) {
    throw new Error('找不到该 Paste 的管理密钥，无法启用编辑共享')
  }

  return {
    pasteId: parsed.pasteId,
    encryptionKey,
    adminKey: shareManualWithEdit.value ? resolved.adminKey : '',
    shareWithEdit: shareManualWithEdit.value
  }
}

async function refreshRoomInfo(): Promise<void> {
  const session = activeRoomSession.value
  if (!session?.pinCode) return

  try {
    const info = await getRoomInfoByPin(session.pinCode)
    syncRoomInfo(info, session.pinCode)
  } catch (error) {
    if (isRoomMissingError(error)) {
      resolveMissingRoom()
    }
    return
  }
}

async function refreshMembers(options: { silent?: boolean } = {}): Promise<void> {
  const session = activeRoomSession.value
  const identity = memberIdentity.value
  if (!session || !identity) return

  isMembersLoading.value = true
  try {
    const response = await getRoomMembers(identity.memberToken, session.roomId)
    members.value = response.members
  } catch (error) {
    if (isRoomMissingError(error)) {
      resolveMissingRoom()
      return
    }
    if (!options.silent) {
      snackbar({
        message: extractErrorMessage(error, '刷新成员列表失败'),
        closeable: true
      })
    }
  } finally {
    isMembersLoading.value = false
  }
}

async function refreshPastes(options: { silent?: boolean } = {}): Promise<void> {
  const session = activeRoomSession.value
  const identity = memberIdentity.value
  if (!session || !identity) return

  isPastesLoading.value = true
  try {
    const response = await getRoomPastes(identity.memberToken, session.roomId, 'all')
    pastes.value = response.pastes
    rememberVisibleUnreadPastes()
  } catch (error) {
    if (isRoomMissingError(error)) {
      resolveMissingRoom()
      return
    }
    if (!options.silent) {
      snackbar({
        message: extractErrorMessage(error, '刷新共享内容失败'),
        closeable: true
      })
    }
  } finally {
    isPastesLoading.value = false
  }
}

function handleRealtimeEvent(event: RoomRealtimeEvent): void {
  if (event.type === 'member_joined' || event.type === 'member_left') {
    void Promise.all([refreshRoomInfo(), refreshMembers({ silent: true })])
    return
  }

  if (event.type === 'paste_shared') {
    if (!selfMemberId.value) {
      void refreshPastes({ silent: true })
      return
    }
    if (event.shared_by === selfMemberId.value) {
      void refreshPastes({ silent: true })
      return
    }
    if (event.target_member && event.target_member !== selfMemberId.value) {
      void refreshPastes({ silent: true })
      return
    }
    markUnreadPaste(activeRoomSession.value?.roomId, buildUnreadPasteKey(event.paste_id, event.timestamp))
    void refreshPastes({ silent: true })
  }
}

async function connectRealtime(): Promise<void> {
  const session = activeRoomSession.value
  const identity = memberIdentity.value
  if (!session || !identity) return

  await connect({
    roomId: session.roomId,
    wsUrl: session.wsUrl,
    memberToken: identity.memberToken,
    onEvent: handleRealtimeEvent
  })
}

function syncOpenState(): void {
  activeTab.value = resolveWorkspaceTab(workspaceDialogIntent.value)
  selectedShareSource.value = currentShareUnavailable.value ? 'manual' : 'current'
  selectedHistoryPasteId.value = ''
  manualInputExpanded.value = false
  manualShareError.value = ''
  manualShareInput.value = ''
  shareHistoryWithEdit.value = true
  shareTargetMemberId.value = null
  closeHistoryPicker()
}

async function bootstrapWorkspace(): Promise<void> {
  if (!activeRoomSession.value || !memberIdentity.value) {
    closeWorkspaceDialog()
    return
  }

  isResolvingMissingRoom.value = false
  syncOpenState()

  try {
    await Promise.all([
      refreshRoomInfo(),
      refreshMembers({ silent: true }),
      refreshPastes({ silent: true }),
      connectRealtime()
    ])
    rememberVisibleUnreadPastes()
  } catch (error) {
    snackbar({
      message: extractErrorMessage(error, '加载协作工作区失败'),
      closeable: true
    })
  }
}

function handleSelectShareTarget(memberId: string): void {
  shareTargetMemberId.value = shareTargetMemberId.value === memberId ? null : memberId
}

function handleBroadcastTarget(): void {
  shareTargetMemberId.value = null
}

async function handleShareSelectedSource(): Promise<void> {
  const session = activeRoomSession.value
  const identity = memberIdentity.value
  const roomKey = roomKeyBytes.value
  if (!session || !identity || !roomKey) {
    snackbar({ message: '房间会话缺失，无法分享', closeable: true })
    return
  }

  isSharing.value = true
  manualShareError.value = ''
  try {
    const resolved = await resolveSelectedShareSource()
    const pasteKeyBytes = urlSafeStrToKey(resolved.encryptionKey)
    const encryptedPasteKey = await encryptWithKey(pasteKeyBytes, roomKey)

    let encryptedAdminKey: string | undefined
    if (resolved.shareWithEdit && resolved.adminKey) {
      const adminKeyBytes = new TextEncoder().encode(resolved.adminKey)
      encryptedAdminKey = bytesToStr(await encryptWithKey(adminKeyBytes, roomKey))
    }

    await sharePasteToRoom(identity.memberToken, session.roomId, {
      paste_id: resolved.pasteId,
      encrypted_paste_key: bytesToStr(encryptedPasteKey),
      encrypted_admin_key: encryptedAdminKey,
      target_member_id: shareTargetMemberId.value || undefined
    })

    snackbar({ message: 'Paste 已发送到房间' })
    emit('sharedCurrentPaste')
    await refreshPastes({ silent: true })
    activeTab.value = 'shared'
  } catch (error) {
    const message = extractErrorMessage(error, '分享 Paste 失败')
    if (selectedShareSource.value === 'manual') {
      manualShareError.value = message
    }
    snackbar({ message, closeable: true })
  } finally {
    isSharing.value = false
  }
}

async function openSharedPasteForEdit(paste: SharedPasteRecord, roomKey: Uint8Array): Promise<void> {
  if (!paste.encrypted_admin_key) throw new Error('该共享记录不包含编辑权限')

  const decryptedPasteKey = await decryptWithKey(strToBytes(paste.encrypted_paste_key), roomKey)
  const decryptedAdminKey = await decryptWithKey(strToBytes(paste.encrypted_admin_key), roomKey)
  const encryptionKey = keyToUrlSafeStr(decryptedPasteKey)
  const adminKey = new TextDecoder().decode(decryptedAdminKey)

  sessionStorage.setItem(
    EDIT_CONTEXT_STORAGE_KEY,
    JSON.stringify({
      paste_id: paste.paste_id,
      admin_key: adminKey,
      encryption_key: encryptionKey,
      created_at: Date.now()
    })
  )

  closeWorkspaceDialog()
  await router.push({
    path: '/',
    query: {
      edit: '1',
      paste_id: paste.paste_id
    }
  })
}

async function handleOpenSharedPaste(paste: SharedPasteRecord): Promise<void> {
  const roomKey = roomKeyBytes.value
  if (!roomKey) {
    snackbar({ message: '缺少房间密钥，无法打开 Paste', closeable: true })
    return
  }

  try {
    const decryptedKey = await decryptWithKey(strToBytes(paste.encrypted_paste_key), roomKey)
    const urlSafeKey = keyToUrlSafeStr(decryptedKey)
    window.open(buildAbsoluteAppUrl(`/p/${paste.paste_id}#${urlSafeKey}`), '_blank', 'noopener')
  } catch (error) {
    snackbar({
      message: extractErrorMessage(error, '打开共享 Paste 失败'),
      closeable: true
    })
  }
}

async function handleEditSharedPaste(paste: SharedPasteRecord): Promise<void> {
  const roomKey = roomKeyBytes.value
  if (!roomKey) {
    snackbar({ message: '缺少房间密钥，无法进入编辑', closeable: true })
    return
  }

  try {
    await openSharedPasteForEdit(paste, roomKey)
  } catch (error) {
    snackbar({
      message: extractErrorMessage(error, '进入共享 Paste 编辑失败'),
      closeable: true
    })
  }
}

async function handleCopyPasteLink(paste: SharedPasteRecord): Promise<void> {
  const roomKey = roomKeyBytes.value
  if (!roomKey) {
    snackbar({ message: '缺少房间密钥，无法复制 Paste 链接', closeable: true })
    return
  }

  try {
    const decryptedKey = await decryptWithKey(strToBytes(paste.encrypted_paste_key), roomKey)
    const urlSafeKey = keyToUrlSafeStr(decryptedKey)
    await navigator.clipboard.writeText(buildAbsoluteAppUrl(`/p/${paste.paste_id}#${urlSafeKey}`))
    snackbar({ message: 'Paste 链接已复制' })
  } catch (error) {
    snackbar({
      message: extractErrorMessage(error, '复制 Paste 链接失败'),
      closeable: true
    })
  }
}

async function handleLeaveRoom(): Promise<void> {
  if (isLeaving.value) return

  isLeaving.value = true
  try {
    clearRoomUnreadState(activeRoomSession.value?.roomId)
    await leaveActiveRoom()
    closeWorkspaceDialog()
    snackbar({ message: '已离开房间' })
  } catch (error) {
    snackbar({
      message: extractErrorMessage(error, '离开房间失败'),
      closeable: true
    })
  } finally {
    isLeaving.value = false
  }
}

function handleDialogClosed(): void {
  commitViewedUnreadPastes()
  closeWorkspaceDialog()
  closeHistoryPicker()
  disconnect()
}

watch(
  isWorkspaceDialogOpen,
  (open) => {
    if (dialogRef.value) {
      dialogRef.value.open = open
    }

    if (open) {
      void bootstrapWorkspace()
      return
    }

    commitViewedUnreadPastes()
    disconnect()
  },
  { immediate: true }
)

watch(
  isHistoryPickerOpen,
  (open) => {
    if (historyDialogRef.value) {
      historyDialogRef.value.open = open
    }
  },
  { immediate: true }
)

watch(
  activeRoomSession,
  (session) => {
    if (!session && isWorkspaceDialogOpen.value) {
      closeWorkspaceDialog()
      disconnect()
    }
  }
)

watch(
  () => workspaceDialogIntent.value,
  (intent) => {
    if (!isWorkspaceDialogOpen.value) return
    activeTab.value = resolveWorkspaceTab(intent)
    rememberVisibleUnreadPastes()
  }
)

watch(
  () => props.currentPasteId,
  (pasteId) => {
    if (pasteId) return
    if (selectedShareSource.value === 'current') {
      selectedShareSource.value = 'manual'
    }
    manualInputExpanded.value = false
  }
)

onBeforeUnmount(() => {
  commitViewedUnreadPastes()
  closeHistoryPicker()
  disconnect()
})
</script>

<style scoped>
.collab-workspace-dialog {
  padding: 1rem;
}

.collab-workspace-dialog::part(panel) {
  width: min(92vw, 500px);
  max-width: 500px;
  padding: 0;
  overflow: hidden;
  border-radius: 24px;
  background:
    linear-gradient(
      180deg,
      rgb(var(--mdui-color-surface-container-low)) 0%,
      rgb(var(--mdui-color-surface)) 100%
    );
}

.dialog-shell {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  max-height: min(88vh, 760px);
  overflow: hidden;
  color: rgb(var(--mdui-color-on-surface));
}

.room-sheet {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  background: rgb(var(--mdui-color-surface));
}

.sheet-header {
  padding: 16px 18px 14px;
  text-align: center;
  color: rgb(var(--mdui-color-on-secondary-container));
  background: rgb(var(--mdui-color-secondary-container));
}

.sheet-header h2 {
  margin: 0;
  font-size: 1.18rem;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: rgb(var(--mdui-color-secondary));
}

.sheet-header h3 {
  margin: 8px 0 0;
  font-size: 0.98rem;
  font-weight: 500;
  color: rgb(var(--mdui-color-on-secondary-container));
}

.sheet-subtitle {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 10px 14px;
}

.sheet-subtitle-separator {
  opacity: 0.72;
}

.workspace-tabs {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  --shape-corner-small: 18px;
}

.tab-panel {
  display: grid;
  gap: 14px;
  padding: 18px 22px 0;
}

.shared-tab-panel {
  min-height: 0;
}

.panel-card {
  display: grid;
  gap: 14px;
  padding: 18px;
  border-radius: 24px;
  background: rgb(var(--mdui-color-surface-container-low));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-outline-variant) / 0.4);
}

.panel-copy {
  display: grid;
  gap: 6px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-copy h4 {
  margin: 0;
  font-size: 1rem;
}

.panel-copy p,
.source-card p,
.source-hint,
.share-status,
.paste-main p,
.paste-meta,
.empty-block {
  margin: 0;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.source-stack {
  display: grid;
  gap: 12px;
}

.source-card {
  box-sizing: border-box;
  display: grid;
  gap: 16px;
  width: 100%;
  padding: 16px;
  text-align: left;
  border-radius: 22px;
  color: rgb(var(--mdui-color-on-surface));
  background: rgb(var(--mdui-color-surface));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-outline-variant) / 0.5);
  cursor: pointer;
  transition: box-shadow 0.18s ease, background-color 0.18s ease, transform 0.18s ease;
}

.source-card.active {
  background: rgb(var(--mdui-color-primary-container));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-primary) / 0.35);
}

.source-card:hover {
  transform: translateY(-1px);
}

.source-label {
  display: block;
  margin-bottom: 10px;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: rgb(var(--mdui-color-secondary));
}

.source-card strong {
  display: block;
  font-size: 1.06rem;
  line-height: 1.3;
}

.source-card p {
  margin-top: 8px;
}

.source-card-main {
  display: grid;
  gap: 0;
}

.inline-edit-switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface));
}

.source-shortcuts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.manual-toggle {
  width: 100%;
}

.manual-toggle.active {
  --container-color: rgb(var(--mdui-color-primary-container));
  --label-text-color: rgb(var(--mdui-color-on-primary-container));
}

.source-body {
  box-sizing: border-box;
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 22px;
  background: rgb(var(--mdui-color-surface));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-outline-variant) / 0.45);
}

.edit-switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
  color: rgb(var(--mdui-color-on-surface));
}

.source-hint {
  min-height: 1.4em;
  line-height: 1.45;
}

.source-hint-error {
  color: rgb(var(--mdui-color-error));
}

.share-status {
  line-height: 1.45;
}

.target-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.target-pill {
  appearance: none;
  border: 0;
  padding: 10px 18px;
  border-radius: 999px;
  font: inherit;
  font-weight: 700;
  color: rgb(var(--mdui-color-on-surface));
  background: rgb(var(--mdui-color-surface));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-outline-variant));
  cursor: pointer;
  transition: background-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.target-pill.active {
  color: rgb(var(--mdui-color-on-primary));
  background: rgb(var(--mdui-color-primary));
}

.target-pill[data-online='true']:not(.active) {
  color: rgb(var(--mdui-color-on-primary-container));
  background: rgb(var(--mdui-color-primary-container));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-primary) / 0.18);
}

.target-pill-broadcast:not(.active) {
  color: rgb(var(--mdui-color-on-primary-container));
  background: rgb(var(--mdui-color-primary-container));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-primary) / 0.18);
}

.target-pill[data-online='false'] {
  opacity: 0.68;
}

.target-panel mdui-button {
  width: 100%;
}

.paste-list {
  display: grid;
  gap: 14px;
}

.paste-panel {
  min-height: 0;
  grid-template-rows: auto minmax(0, 1fr);
  max-height: clamp(260px, 52vh, 480px);
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
}

.paste-panel-body {
  min-height: 0;
  overflow: visible;
}

.history-picker-dialog {
  padding: 1rem;
}

.history-picker-dialog::part(panel) {
  width: min(92vw, 500px);
  max-width: 500px;
  padding: 0;
  overflow: hidden;
  border-radius: 24px;
  background:
    linear-gradient(
      180deg,
      rgb(var(--mdui-color-surface-container-low)) 0%,
      rgb(var(--mdui-color-surface)) 100%
    );
}

.history-picker-body {
  display: grid;
  gap: 14px;
  padding: 18px 22px 0;
}

.history-picker-list {
  display: grid;
  gap: 12px;
}

.history-picker-item {
  box-sizing: border-box;
  appearance: none;
  border: 0;
  display: grid;
  gap: 8px;
  width: 100%;
  padding: 16px;
  text-align: left;
  border-radius: 22px;
  color: rgb(var(--mdui-color-on-surface));
  background: rgb(var(--mdui-color-surface-container-low));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-outline-variant) / 0.45);
  cursor: pointer;
  transition: box-shadow 0.18s ease, background-color 0.18s ease, transform 0.18s ease;
}

.history-picker-item:hover {
  transform: translateY(-1px);
}

.history-picker-item.active {
  background: rgb(var(--mdui-color-primary-container));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-primary) / 0.35);
}

.history-picker-copy {
  display: grid;
  gap: 6px;
}

.history-picker-copy strong {
  font-size: 1rem;
  line-height: 1.35;
}

.history-picker-copy p,
.history-picker-meta {
  margin: 0;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.history-picker-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 0.92rem;
}

.paste-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: 22px;
  background: rgb(var(--mdui-color-surface));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-outline-variant) / 0.45);
}

.paste-card.unread {
  background: rgb(var(--mdui-color-primary-container));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-primary) / 0.35);
}

.paste-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.paste-main h5 {
  margin: 0 0 8px;
  font-size: 1.06rem;
}

.paste-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 0.92rem;
}

.paste-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.empty-block {
  padding: 20px 8px 4px;
  text-align: center;
  line-height: 1.55;
}

.dialog-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 14px 16px 16px;
}

.dialog-actions mdui-button {
  width: 100%;
}

.history-dialog-actions {
  grid-template-columns: auto;
  justify-content: end;
}

.history-dialog-actions mdui-button {
  width: auto;
}

.leave-button {
  --mdui-color-primary: var(--mdui-color-primary-container);
  --mdui-color-on-primary: var(--mdui-color-on-primary-container);
}

@media (max-width: 640px) {
  .collab-workspace-dialog {
    padding: 4px;
  }

  .collab-workspace-dialog::part(panel) {
    width: calc(100vw - 8px);
    max-width: calc(100vw - 8px);
    border-radius: 16px;
  }

  .dialog-shell {
    max-height: min(86vh, 700px);
  }

  .sheet-header {
    padding: 14px 10px 12px;
  }

  .sheet-header h2 {
    font-size: 1.24rem;
  }

  .tab-panel {
    padding: 12px 8px 0;
  }

  .paste-panel {
    max-height: clamp(220px, 46vh, 420px);
  }

  .history-picker-body {
    padding: 12px 8px 0;
  }

  .panel-card {
    padding: 16px;
  }

  .panel-head,
  .paste-main {
    display: grid;
    gap: 10px;
  }

  .paste-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
  }

  .edit-switch-row {
    align-items: flex-start;
  }

  .dialog-actions {
    padding: 12px 8px 10px;
  }

  .history-picker-dialog {
    padding: 4px;
  }

  .history-picker-dialog::part(panel) {
    width: calc(100vw - 8px);
    max-width: calc(100vw - 8px);
    border-radius: 16px;
  }
}
</style>
