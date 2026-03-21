<template>
  <div class="room-page">
    <section class="room-topbar">
      <div class="room-hero surface-card">
        <p class="room-kicker">ROOM WORKSPACE</p>
        <div class="room-hero-main">
          <div>
            <h1>{{ activeRoomSession?.roomName || '协作房间' }}</h1>
            <p class="room-subtitle">
              邀请码 {{ activeRoomSession?.pinCode || '—' }} · 成员上限 {{ activeRoomSession?.maxMembers ?? '—' }}
            </p>
          </div>

          <div class="hero-actions">
            <mdui-button variant="outlined" @click="handleCopyJoinLink">复制邀请链接</mdui-button>
            <mdui-button variant="text" @click="handleLeaveRoom">离开房间</mdui-button>
          </div>
        </div>
      </div>

      <div class="connection-banner" :data-state="realtimeStatus">
        <div class="banner-copy">
          <strong>{{ connectionHeadline }}</strong>
          <span>{{ connectionDetail }}</span>
        </div>
        <mdui-button v-if="realtimeStatus !== 'connected'" variant="tonal" @click="handleReconnectRealtime">
          重新连接
        </mdui-button>
      </div>
    </section>

    <section class="room-layout">
      <aside class="room-sidebar">
        <section class="surface-card member-panel" :aria-busy="isMembersLoading ? 'true' : 'false'">
          <div class="panel-header">
            <div>
              <p class="panel-kicker">成员</p>
              <h2>在线席位</h2>
            </div>
            <mdui-button variant="text" @click="refreshMembers">刷新</mdui-button>
          </div>

          <div v-if="members.length === 0 && !isMembersLoading" class="empty-block">
            暂无成员信息
          </div>

          <div v-else class="member-list">
            <article v-for="member in members" :key="member.member_id" class="member-card">
              <div class="member-main">
                <div>
                  <strong>{{ member.display_name }}</strong>
                  <p>{{ member.member_id === selfMemberId ? '你' : formatLastSeen(member.last_seen) }}</p>
                </div>
                <span class="member-status" :data-online="member.is_online ? 'true' : 'false'">
                  {{ member.is_online ? '在线' : '离线' }}
                </span>
              </div>
              <button
                type="button"
                class="target-chip"
                :class="{ active: shareTargetMemberId === member.member_id }"
                :disabled="member.member_id === selfMemberId"
                @click="handleSelectShareTarget(member.member_id)"
              >
                {{ member.member_id === selfMemberId ? '自己' : '私发给此成员' }}
              </button>
            </article>
          </div>
        </section>
      </aside>

      <main class="room-main">
        <section class="surface-card share-panel">
          <div class="panel-header">
            <div>
              <p class="panel-kicker">分享 Paste</p>
              <h2>投递新的内容</h2>
            </div>
          </div>

          <div class="share-grid">
            <mdui-text-field
              v-model="shareForm.reference"
              class="share-reference"
              label="Paste 链接或 Paste ID"
              variant="outlined"
              clearable
            ></mdui-text-field>
            <mdui-text-field
              v-model="shareForm.key"
              label="Paste 解密密钥（若链接中已带 hash 可留空）"
              variant="outlined"
              clearable
            ></mdui-text-field>
          </div>

          <div class="share-target-row">
            <div class="share-target-copy">
              <strong>发送范围</strong>
              <span>{{ shareTargetLabel }}</span>
            </div>
            <mdui-button variant="text" @click="handleBroadcastTarget">发送给全部成员</mdui-button>
          </div>

          <div class="panel-footer">
            <span class="hint-copy">共享事件到达后会重新拉取 Paste 列表，确保卡片信息以服务端快照为准。</span>
            <mdui-button variant="filled" :loading="isSharing" @click="handleSharePaste">
              分享 Paste
            </mdui-button>
          </div>
        </section>

        <section class="surface-card paste-panel" :aria-busy="isPastesLoading ? 'true' : 'false'">
          <div class="panel-header paste-header">
            <div>
              <p class="panel-kicker">共享内容</p>
              <h2>房间 Paste 列表</h2>
            </div>

            <mdui-segmented-button-group :value="pasteFilter" selects="single" @change="handlePasteFilterChange">
              <mdui-segmented-button value="received">收到的</mdui-segmented-button>
              <mdui-segmented-button value="sent">发出的</mdui-segmented-button>
              <mdui-segmented-button value="all">全部</mdui-segmented-button>
            </mdui-segmented-button-group>
          </div>

          <div v-if="pastes.length === 0 && !isPastesLoading" class="empty-block">
            当前筛选下还没有共享 Paste。
          </div>

          <div v-else class="paste-list">
            <article v-for="paste in pastes" :key="`${paste.paste_id}-${paste.shared_at}`" class="paste-card">
              <div class="paste-main">
                <div>
                  <h3>{{ paste.title || paste.paste_id }}</h3>
                  <p>
                    来自 {{ memberName(paste.shared_by) }}
                    <template v-if="paste.target_member"> · 指向 {{ memberName(paste.target_member) }}</template>
                  </p>
                </div>
                <span class="paste-state" :data-expired="paste.is_expired ? 'true' : 'false'">
                  {{ paste.is_expired ? '已过期' : '可打开' }}
                </span>
              </div>

              <div class="paste-meta">
                <span>{{ formatDateTime(paste.shared_at) }}</span>
                <span v-if="paste.expire_at">过期于 {{ formatDateTime(paste.expire_at) }}</span>
              </div>

              <div class="paste-actions">
                <mdui-button variant="tonal" :disabled="paste.is_expired" @click="handleOpenSharedPaste(paste)">
                  打开 Paste
                </mdui-button>
                <mdui-button variant="text" @click="handleCopyPasteLink(paste.paste_id)">
                  复制链接
                </mdui-button>
              </div>
            </article>
          </div>
        </section>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import 'mdui/components/button.js'
import 'mdui/components/icon.js'
import 'mdui/components/segmented-button-group.js'
import 'mdui/components/segmented-button.js'
import 'mdui/components/text-field.js'
import { dialog } from 'mdui/functions/dialog.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import { useRoomRealtime, type RoomRealtimeEvent } from '../composables/useRoomRealtime'
import { useRoomSession } from '../composables/useRoomSession'
import {
  getRoomInfoByPin,
  getRoomMembers,
  getRoomPastes,
  leaveRoom,
  sharePasteToRoom,
  type RoomMember,
  type RoomPasteFilter,
  type SharedPasteRecord
} from '../services/rooms'
import { buildAbsoluteAppUrl } from '../utils/appUrl'
import { bytesToStr, decryptWithKey, encryptWithKey, keyToUrlSafeStr, strToBytes, urlSafeStrToKey } from '../utils/crypto'

const route = useRoute()
const router = useRouter()
const { memberIdentity, roomKeyBytes, requireActiveRoom, clearActiveRoom, syncRoomInfo } = useRoomSession()
const {
  status: realtimeStatusRef,
  statusMessage,
  selfMemberId,
  lastPongAt,
  connect,
  disconnect,
  reconnect
} = useRoomRealtime()

const roomId = computed(() => String(route.params.roomId || '').trim())
const activeRoomSession = computed(() => requireActiveRoom(roomId.value))
const realtimeStatus = computed(() => realtimeStatusRef.value)

const members = ref<RoomMember[]>([])
const pastes = ref<SharedPasteRecord[]>([])
const pasteFilter = ref<RoomPasteFilter>('received')
const isMembersLoading = ref(false)
const isPastesLoading = ref(false)
const isSharing = ref(false)

const shareForm = reactive({
  reference: '',
  key: ''
})
const shareTargetMemberId = ref<string | null>(null)

const connectionHeadline = computed(() => {
  if (realtimeStatus.value === 'connected') return '实时通道在线'
  if (realtimeStatus.value === 'connecting') return '正在建立实时通道'
  if (realtimeStatus.value === 'closed') return '实时通道已关闭'
  if (realtimeStatus.value === 'error') return '实时通道异常'
  return '实时通道尚未启动'
})

const connectionDetail = computed(() => {
  if (realtimeStatus.value === 'connected') {
    return lastPongAt.value ? `最后心跳 ${formatDateTime(lastPongAt.value)}` : '连接已认证，可以接收成员与 Paste 事件'
  }

  return statusMessage.value || '房间实时状态未知'
})

const shareTargetLabel = computed(() => {
  if (!shareTargetMemberId.value) return '群发给当前房间内所有成员'
  return `仅发送给 ${memberName(shareTargetMemberId.value)}`
})

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

function formatLastSeen(value: string): string {
  const parsed = new Date(/(Z|[+\-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`)
  if (Number.isNaN(parsed.getTime())) return '最近活跃时间未知'
  const diffMs = Math.max(0, Date.now() - parsed.getTime())
  const diffMin = Math.round(diffMs / 60000)
  if (diffMin < 1) return '刚刚活跃'
  if (diffMin < 60) return `${diffMin} 分钟前活跃`
  return formatDateTime(value)
}

function normalizePasteReference(rawReference: string, rawKey: string): { pasteId: string; pasteKey: string } {
  const reference = rawReference.trim()
  const explicitKey = rawKey.trim()
  let pasteId = ''
  let derivedKey = explicitKey

  if (!reference) {
    throw new Error('请提供 Paste 链接或 Paste ID')
  }

  try {
    const url = new URL(reference, window.location.origin)
    const match = url.pathname.match(/\/p\/([^/]+)/)
    pasteId = match?.[1] ? decodeURIComponent(match[1]) : ''
    if (!derivedKey && url.hash) {
      derivedKey = url.hash.slice(1)
    }
  } catch (_error) {
    pasteId = ''
  }

  if (!pasteId) {
    pasteId = reference.replace(/^\/p\//, '').trim()
  }

  if (!pasteId) {
    throw new Error('无法识别 Paste ID')
  }

  if (!derivedKey) {
    throw new Error('缺少 Paste 解密密钥')
  }

  return { pasteId, pasteKey: derivedKey }
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
    const response = await getRoomPastes(identity.memberToken, session.roomId, pasteFilter.value)
    pastes.value = response.pastes
  } catch (error) {
    if (!options.silent) {
      snackbar({
        message: extractErrorMessage(error, '刷新 Paste 列表失败'),
        closeable: true
      })
    }
  } finally {
    isPastesLoading.value = false
  }
}

async function refreshRoomInfo(): Promise<void> {
  const session = activeRoomSession.value
  if (!session?.pinCode) return

  try {
    const info = await getRoomInfoByPin(session.pinCode)
    syncRoomInfo(info, session.pinCode)
  } catch (_error) {
    return
  }
}

function handleRealtimeEvent(event: RoomRealtimeEvent): void {
  if (event.type === 'member_joined' || event.type === 'member_left') {
    void refreshMembers({ silent: true })
    return
  }

  if (event.type === 'paste_shared') {
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

async function bootstrapRoom(): Promise<void> {
  const session = activeRoomSession.value
  const identity = memberIdentity.value

  if (!roomId.value || !session || session.roomId !== roomId.value || !identity) {
      snackbar({ message: '当前标签页没有可恢复的房间会话', closeable: true })
      await router.replace('/')
    return
  }

  try {
    await Promise.all([
      refreshRoomInfo(),
      refreshMembers({ silent: true }),
      refreshPastes({ silent: true }),
      connectRealtime()
    ])
  } catch (error) {
    snackbar({
      message: extractErrorMessage(error, '加载房间数据失败'),
      closeable: true
    })
  }
}

function handleSelectShareTarget(memberId: string): void {
  if (memberId === selfMemberId.value) return
  shareTargetMemberId.value = shareTargetMemberId.value === memberId ? null : memberId
}

function handleBroadcastTarget(): void {
  shareTargetMemberId.value = null
}

function eventValue(event: Event): string {
  const target = event.target as HTMLInputElement | { value?: unknown } | null
  const value = target && 'value' in target ? target.value : ''
  return typeof value === 'string' ? value : value == null ? '' : String(value)
}

async function handlePasteFilterChange(event: Event): Promise<void> {
  const nextFilter = eventValue(event)
  if (nextFilter !== 'received' && nextFilter !== 'sent' && nextFilter !== 'all') {
    return
  }

  pasteFilter.value = nextFilter
  await refreshPastes()
}

async function handleSharePaste(): Promise<void> {
  const session = activeRoomSession.value
  const identity = memberIdentity.value
  const roomKey = roomKeyBytes.value
  if (!session || !identity || !roomKey) {
    snackbar({ message: '房间会话缺失，无法分享', closeable: true })
    return
  }

  isSharing.value = true
  try {
    const parsed = normalizePasteReference(shareForm.reference, shareForm.key)
    const pasteKeyBytes = urlSafeStrToKey(parsed.pasteKey)
    const encryptedPasteKey = await encryptWithKey(pasteKeyBytes, roomKey)

    await sharePasteToRoom(identity.memberToken, session.roomId, {
      paste_id: parsed.pasteId,
      encrypted_paste_key: bytesToStr(encryptedPasteKey),
      target_member_id: shareTargetMemberId.value || undefined
    })

    shareForm.reference = ''
    shareForm.key = ''
    shareTargetMemberId.value = null
    snackbar({ message: 'Paste 已发送到房间' })
    await refreshPastes()
  } catch (error) {
    snackbar({
      message: error instanceof Error ? error.message : '分享 Paste 失败',
      closeable: true
    })
  } finally {
    isSharing.value = false
  }
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
    await router.push(`/p/${paste.paste_id}#${urlSafeKey}`)
  } catch (error) {
    snackbar({
      message: error instanceof Error ? error.message : '解密共享 Paste 密钥失败',
      closeable: true
    })
  }
}

async function handleCopyJoinLink(): Promise<void> {
  const joinUrl = activeRoomSession.value?.joinUrl
  if (!joinUrl) return

  try {
    await navigator.clipboard.writeText(joinUrl)
    snackbar({ message: '邀请链接已复制' })
  } catch (_error) {
    snackbar({ message: '复制邀请链接失败', closeable: true })
  }
}

async function handleCopyPasteLink(pasteId: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(buildAbsoluteAppUrl(`/p/${pasteId}`))
    snackbar({ message: 'Paste 链接已复制' })
  } catch (_error) {
    snackbar({ message: '复制 Paste 链接失败', closeable: true })
  }
}

async function performLeaveRoom(): Promise<void> {
  const session = activeRoomSession.value
  const identity = memberIdentity.value
  if (!session || !identity) {
    clearActiveRoom()
    await router.replace('/')
    return
  }

  try {
    await leaveRoom(identity.memberToken, session.roomId)
  } catch (error) {
    snackbar({
      message: error instanceof Error ? error.message : '离开房间失败',
      closeable: true
    })
    return
  }

  disconnect()
  clearActiveRoom()
  await router.replace('/')
}

function handleLeaveRoom(): void {
  dialog({
    headline: '离开房间',
    description: '离开后将断开实时连接，并清除当前标签页保存的房间引导信息。',
    actions: [
      { text: '取消' },
      {
        text: '离开',
        onClick: () => {
          void performLeaveRoom()
        }
      }
    ]
  })
}

async function handleReconnectRealtime(): Promise<void> {
  try {
    await Promise.all([refreshMembers({ silent: true }), refreshPastes({ silent: true })])
    await reconnect()
  } catch (error) {
    snackbar({
      message: extractErrorMessage(error, '重新连接失败'),
      closeable: true
    })
  }
}

onMounted(() => {
  void bootstrapRoom()
})

onBeforeUnmount(() => {
  disconnect()
})

watch(
  () => route.params.roomId,
  (nextRoomId, previousRoomId) => {
    if (nextRoomId && nextRoomId !== previousRoomId) {
      void bootstrapRoom()
    }
  }
)
</script>

<style scoped>
.room-page {
  display: grid;
  gap: 18px;
  padding: 24px 0 32px;
}

.surface-card {
  padding: 20px;
  border-radius: 24px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.72);
  background: rgb(var(--mdui-color-surface));
}

.room-topbar {
  display: grid;
  gap: 14px;
}

.room-hero {
  background:
    radial-gradient(circle at top right, rgb(var(--mdui-color-primary) / 0.15), transparent 30%),
    linear-gradient(160deg, rgb(var(--mdui-color-surface-container-low)) 0%, rgb(var(--mdui-color-surface)) 100%);
}

.room-kicker,
.panel-kicker {
  margin: 0;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgb(var(--mdui-color-primary));
}

.room-hero-main,
.hero-actions,
.panel-header,
.paste-main,
.paste-actions,
.panel-footer,
.share-target-row,
.member-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.room-hero-main {
  margin-top: 10px;
  align-items: flex-end;
}

.room-hero h1,
.panel-header h2,
.paste-card h3 {
  margin: 0;
}

.room-subtitle,
.hint-copy,
.paste-main p,
.paste-meta,
.member-main p,
.share-target-copy span {
  margin: 0;
  color: rgb(var(--mdui-color-on-surface-variant));
  line-height: 1.55;
}

.connection-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 18px;
  border-radius: 18px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.7);
  background: rgb(var(--mdui-color-surface-container-low));
}

.connection-banner[data-state='connected'] {
  background: rgb(var(--mdui-color-primary-container) / 0.38);
}

.connection-banner[data-state='error'] {
  background: rgb(var(--mdui-color-error-container) / 0.42);
}

.banner-copy {
  display: grid;
  gap: 4px;
}

.room-layout {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(0, 1.4fr);
  gap: 18px;
  align-items: start;
}

.room-sidebar,
.room-main,
.member-panel,
.share-panel,
.paste-panel,
.member-list,
.paste-list {
  display: grid;
  gap: 16px;
}

.member-card,
.paste-card {
  padding: 16px;
  border-radius: 18px;
  background: rgb(var(--mdui-color-surface-container-low));
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.52);
}

.member-status,
.paste-state {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 0.78rem;
  background: rgb(var(--mdui-color-surface-container-high));
}

.member-status[data-online='true'],
.paste-state[data-expired='false'] {
  background: rgb(var(--mdui-color-primary-container));
  color: rgb(var(--mdui-color-on-primary-container));
}

.paste-state[data-expired='true'] {
  background: rgb(var(--mdui-color-error-container));
  color: rgb(var(--mdui-color-on-error-container));
}

.target-chip {
  margin-top: 12px;
  padding: 10px 12px;
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgb(var(--mdui-color-outline-variant) / 0.68);
  background: transparent;
  color: rgb(var(--mdui-color-on-surface));
  cursor: pointer;
  transition: background-color 150ms ease, border-color 150ms ease, transform 150ms ease;
}

.target-chip:hover:not(:disabled),
.target-chip.active {
  background: rgb(var(--mdui-color-primary-container) / 0.5);
  border-color: rgb(var(--mdui-color-primary) / 0.42);
}

.target-chip:disabled {
  opacity: 0.6;
  cursor: default;
}

.share-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 14px;
}

.share-reference {
  min-width: 0;
}

.share-target-copy {
  display: grid;
  gap: 4px;
}

.empty-block {
  padding: 24px 16px;
  border-radius: 18px;
  background: rgb(var(--mdui-color-surface-container-low));
  color: rgb(var(--mdui-color-on-surface-variant));
  text-align: center;
}

.paste-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 10px;
  font-size: 0.85rem;
}

.paste-actions {
  margin-top: 14px;
  justify-content: flex-start;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .room-layout,
  .share-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .room-page {
    padding-top: 18px;
  }

  .surface-card {
    padding: 16px;
  }

  .room-hero-main,
  .hero-actions,
  .panel-header,
  .share-target-row,
  .connection-banner {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
