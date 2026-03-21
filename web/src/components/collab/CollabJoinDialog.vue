<template>
  <mdui-dialog
    ref="dialogRef"
    class="collab-join-dialog"
    :class="{ 'invite-dialog-mode': isInviteMode }"
    close-on-esc
    close-on-overlay-click
    @closed="handleDialogClosed"
  >
    <template v-if="isInviteMode">
      <mdui-icon slot="icon" name="group_add" class="invite-dialog-icon"></mdui-icon>
      <div class="invite-dialog-content">
        <div v-if="isLoadingInviteInfo" class="invite-state" role="status" aria-live="polite">
          <mdui-circular-progress></mdui-circular-progress>
          <span>正在确认房间信息…</span>
        </div>

        <div v-else-if="inviteRoomInfo" class="invite-state invite-state-ready">
          <p>是否加入房间 {{ pendingInvitePin }}？当前已有 {{ inviteRoomInfo.member_count }} 人加入。</p>
        </div>

        <div v-else class="invite-state invite-state-error" role="alert" aria-live="polite">
          <span>{{ inviteInfoError || '当前邀请已失效' }}</span>
        </div>
      </div>

      <div class="invite-dialog-actions">
        <mdui-button variant="text" @click="handleDismissInvite">
          {{ inviteRoomInfo ? '暂不加入' : '返回编辑器' }}
        </mdui-button>
        <mdui-button
          v-if="inviteRoomInfo"
          variant="filled"
          :loading="isJoiningInvite"
          @click="handleAcceptInvite"
        >
          加入房间
        </mdui-button>
      </div>
    </template>

    <div v-else class="dialog-shell">
        <section class="room-sheet">
        <header class="sheet-header">
          <h2>协作房间</h2>
        </header>

        <div
          v-if="isCreatingRoom || isCheckingActiveRoom || (!displayedRoom && !createRoomError && !isClosingAfterLeave)"
          class="sheet-loading"
          role="status"
          aria-live="polite"
        >
          <mdui-circular-progress></mdui-circular-progress>
          <span>{{ isCheckingActiveRoom ? '正在确认房间状态…' : '正在创建临时房间…' }}</span>
        </div>

        <div v-else-if="displayedRoom" class="sheet-body">
          <div class="qr-frame">
            <QrCode :value="displayedRoom.joinUrl" :size="qrCodeSize" />
          </div>

          <button
            type="button"
            class="pin-code pin-code-button"
            aria-label="点击复制当前房间码"
            @click="handleCopyPinCode"
          >
            {{ spacedPinCode }}
          </button>

          <p class="sheet-description">扫码或输入房间码加入。</p>
          <p class="sheet-meta">{{ displayedRoom.memberCount ?? 1 }}/{{ displayedRoom.maxMembers ?? '—' }} 人已加入</p>

          <div class="sheet-actions">
            <mdui-button variant="tonal" @click="handleCopyRoomLink">复制房间链接</mdui-button>
            <mdui-button variant="text" :loading="isLeaving" @click="handleLeaveRoom">离开房间</mdui-button>
          </div>
        </div>

        <div v-else class="sheet-empty">
          <h3>创建房间失败</h3>
          <p>{{ createRoomError }}</p>
          <mdui-button variant="filled" :loading="isCreatingRoom" @click="handleCreateRoom">
            重新创建房间
          </mdui-button>
        </div>
        </section>

        <section class="join-sheet" aria-labelledby="join-room-title">
          <div class="join-divider">
            <span>或者</span>
          </div>

          <div class="join-body">
            <h3 id="join-room-title">输入房间码加入房间</h3>

            <div class="pin-inputs" @paste="handleJoinPaste">
              <label
                v-for="(_, index) in PIN_LENGTH"
                :key="index"
                class="pin-slot"
                :data-filled="joinPinDigits[index] ? 'true' : 'false'"
              >
                <span class="sr-only">房间码第 {{ index + 1 }} 位</span>
                <input
                  :ref="(el) => handleJoinInputRef(el, index)"
                  :value="joinPinDigits[index]"
                  inputmode="text"
                  autocomplete="off"
                  spellcheck="false"
                  maxlength="1"
                  aria-label="房间码输入框"
                  @input="handleJoinInput(index, $event)"
                  @keydown="handleJoinKeydown(index, $event)"
                />
              </label>
            </div>

            <p
              class="join-hint"
              :class="{ 'join-hint-error': !!joinError }"
              :role="joinError ? 'alert' : undefined"
              :aria-live="joinError ? 'polite' : undefined"
            >
              {{ joinError || '输入 6 位房间码即可加入' }}
            </p>
          </div>
        </section>

        <footer class="dialog-actions">
          <mdui-button variant="text" @click="handleCloseDialog">关闭</mdui-button>
          <mdui-button
            variant="filled"
            :disabled="!canJoin"
            :loading="isJoiningManual"
            @click="handleJoinByInput"
          >
            加入
          </mdui-button>
        </footer>
    </div>
  </mdui-dialog>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import 'mdui/components/button.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/dialog.js'
import 'mdui/components/icon.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import QrCode from '../common/QrCode.vue'
import { useCollabDialogState } from '../../composables/useCollabDialogState'
import { useRoomSession, type ActiveRoomSession } from '../../composables/useRoomSession'
import { getRoomInfoByPin, type RoomInfoResponse } from '../../services/rooms'

type DialogElement = HTMLElement & { open: boolean }

const PIN_LENGTH = 6
const PIN_ALLOWED_CHARS = new Set('ABCDEFGHJKMNPQRSTUVWXYZ0123456789'.split(''))
const PIN_CHAR_REPLACEMENTS: Record<string, string> = {
  O: '0',
  I: '1',
  L: '1'
}

const dialogRef = ref<DialogElement | null>(null)
const joinPinDigits = ref<string[]>(Array.from({ length: PIN_LENGTH }, () => ''))
const joinInputRefs = ref<Array<HTMLInputElement | null>>(Array.from({ length: PIN_LENGTH }, () => null))
const isCreatingRoom = ref(false)
const isLeaving = ref(false)
const isJoiningManual = ref(false)
const isJoiningInvite = ref(false)
const isLoadingInviteInfo = ref(false)
const isCheckingActiveRoom = ref(false)
const isClosingAfterLeave = ref(false)
const inviteRoomInfo = ref<RoomInfoResponse | null>(null)
const inviteInfoError = ref('')
const createRoomError = ref('')
const joinError = ref('')
const qrCodeSize = ref(152)
const closingRoomSnapshot = ref<ActiveRoomSession | null>(null)

let compactMediaQuery: MediaQueryList | null = null

function handleCompactChange(event: MediaQueryListEvent): void {
  syncQrCodeSize(event.matches)
}

const route = useRoute()
const router = useRouter()
const { isJoinDialogOpen, pendingInvitePin, closeJoinDialog, clearPendingInvitePin } = useCollabDialogState()
const {
  activeRoom,
  ensureMemberIdentity,
  createRoomAndJoin,
  joinExistingRoom,
  leaveActiveRoom,
  syncRoomInfo,
  clearActiveRoom
} = useRoomSession()

const joinPin = computed(() => joinPinDigits.value.join(''))
const isInviteMode = computed(() => Boolean(pendingInvitePin.value))
const canJoin = computed(() => /^[A-Z0-9]{6}$/.test(joinPin.value) && !isJoiningManual.value)
const displayedRoom = computed(() => activeRoom.value ?? (isClosingAfterLeave.value ? closingRoomSnapshot.value : null))
const spacedPinCode = computed(() => (displayedRoom.value?.pinCode || '').split('').join(' '))

function normalizePin(raw: string): string {
  return raw
    .toUpperCase()
    .split('')
    .map((ch) => PIN_CHAR_REPLACEMENTS[ch] ?? ch)
    .filter((ch) => PIN_ALLOWED_CHARS.has(ch))
    .join('')
    .slice(0, PIN_LENGTH)
}

function formatJoinError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    if (status === 404) return '房间码不存在，请检查后重试'
    if (status === 409) return '房间已满，暂时无法加入'
    if (status === 403) return '当前身份已失效，请稍后重试'
    if (!status) return '网络连接失败，请检查后重试'
    if (typeof detail === 'string' && detail.trim()) return detail.trim()
  }

  if (error instanceof Error && error.message.trim()) return error.message
  return '加入房间失败，请稍后重试'
}

function handleJoinInputRef(element: Element | { $el?: Element | null } | null, index: number): void {
  if (element && '$el' in element) {
    const target = element.$el
    joinInputRefs.value[index] = target instanceof HTMLInputElement ? target : null
    return
  }
  joinInputRefs.value[index] = element instanceof HTMLInputElement ? element : null
}

function focusJoinInput(index: number): void {
  const input = joinInputRefs.value[index]
  if (!input) return
  input.focus()
  input.select()
}

function resetJoinPin(): void {
  joinPinDigits.value = Array.from({ length: PIN_LENGTH }, () => '')
  joinError.value = ''
}

function applyPin(pin: string, focusLastFilled: boolean = true): void {
  const normalized = normalizePin(pin)
  const nextDigits = Array.from({ length: PIN_LENGTH }, (_, index) => normalized[index] || '')
  joinPinDigits.value = nextDigits

  const nextIndex = Math.min(normalized.length, PIN_LENGTH - 1)
  if (focusLastFilled) {
    void nextTick(() => focusJoinInput(nextIndex))
  }
}

function syncQrCodeSize(matchesCompact: boolean): void {
  qrCodeSize.value = matchesCompact ? 176 : 152
}

function clearInviteState(): void {
  inviteRoomInfo.value = null
  inviteInfoError.value = ''
}

async function loadInviteRoomInfo(): Promise<void> {
  const pin = pendingInvitePin.value
  clearInviteState()

  if (!pin) return
  if (!/^[A-Z0-9]{6}$/.test(pin)) {
    inviteInfoError.value = '邀请房间码格式无效'
    return
  }

  isLoadingInviteInfo.value = true
  try {
    inviteRoomInfo.value = await getRoomInfoByPin(pin)
  } catch (error) {
    inviteInfoError.value = formatJoinError(error)
  } finally {
    isLoadingInviteInfo.value = false
  }
}

async function validateActiveRoom(options: { notify?: boolean } = {}): Promise<boolean> {
  const room = activeRoom.value
  if (!room?.pinCode) return false

  isCheckingActiveRoom.value = true
  try {
    const roomInfo = await getRoomInfoByPin(room.pinCode)
    syncRoomInfo(roomInfo, room.pinCode)
    return true
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      clearActiveRoom()
      if (options.notify !== false) {
        snackbar({ message: '当前房间已不存在，已退出房间', closeable: true })
      }
      return false
    }
    return true
  } finally {
    isCheckingActiveRoom.value = false
  }
}

async function joinTargetRoom(pin: string, roomInfo: RoomInfoResponse): Promise<void> {
  if (activeRoom.value?.roomId === roomInfo.room_id) {
    snackbar({ message: '你已经在这个房间里了' })
    handleCloseDialog()
    return
  }

  if (activeRoom.value) {
    await leaveActiveRoom()
  }

  await joinExistingRoom({
    roomId: roomInfo.room_id,
    pinCode: pin,
    joinUrl: `/join/${pin}`,
    memberCount: Math.min(roomInfo.member_count + 1, roomInfo.max_members),
    maxMembers: roomInfo.max_members
  })

  snackbar({ message: `已加入房间 ${pin}` })
  resetJoinPin()
  clearPendingInvitePin()
  if (route.params.pin) {
    await router.replace('/')
  }
  closeJoinDialog()
}

async function handleCreateRoom(options: { silentSuccess?: boolean } = {}): Promise<void> {
  if (isCreatingRoom.value) return

  isCreatingRoom.value = true
  createRoomError.value = ''
  joinError.value = ''
  try {
    await ensureMemberIdentity()
    await createRoomAndJoin()
    if (!options.silentSuccess) {
      snackbar({ message: '临时房间已创建' })
    }
    if (route.params.pin) {
      await router.replace('/')
      clearPendingInvitePin()
    }
  } catch (error) {
    createRoomError.value = error instanceof Error ? error.message : '创建临时房间失败，请稍后重试'
    snackbar({
      message: createRoomError.value,
      closeable: true
    })
  } finally {
    isCreatingRoom.value = false
  }
}

async function handleAcceptInvite(): Promise<void> {
  if (!pendingInvitePin.value || !inviteRoomInfo.value || isJoiningInvite.value) return

  isJoiningInvite.value = true
  try {
    await joinTargetRoom(pendingInvitePin.value, inviteRoomInfo.value)
  } catch (error) {
    snackbar({
      message: formatJoinError(error),
      closeable: true
    })
  } finally {
    isJoiningInvite.value = false
  }
}

async function handleJoinByInput(): Promise<void> {
  if (!canJoin.value) return

  isJoiningManual.value = true
  joinError.value = ''
  try {
    const pin = joinPin.value
    const roomInfo = await getRoomInfoByPin(pin)
    await joinTargetRoom(pin, roomInfo)
  } catch (error) {
    joinError.value = formatJoinError(error)
  } finally {
    isJoiningManual.value = false
  }
}

async function handleLeaveRoom(): Promise<void> {
  const room = activeRoom.value
  if (!room || isLeaving.value) return

  isLeaving.value = true
  closingRoomSnapshot.value = room
  try {
    await leaveActiveRoom()
    isClosingAfterLeave.value = true
    closeJoinDialog()
    snackbar({ message: '已离开房间' })
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      clearActiveRoom()
      isClosingAfterLeave.value = true
      closeJoinDialog()
      snackbar({ message: '当前房间已不存在，已退出房间', closeable: true })
      return
    }
    closingRoomSnapshot.value = null
    snackbar({
      message: formatJoinError(error),
      closeable: true
    })
  } finally {
    isLeaving.value = false
  }
}

function handleJoinInput(index: number, event: Event): void {
  joinError.value = ''
  const target = event.target as HTMLInputElement | null
  const normalized = normalizePin(target?.value || '')

  if (!normalized) {
    joinPinDigits.value = joinPinDigits.value.map((digit, digitIndex) => (digitIndex === index ? '' : digit))
    return
  }

  if (normalized.length > 1) {
    const prefix = joinPinDigits.value.slice(0, index).join('')
    applyPin(`${prefix}${normalized}`)
    return
  }

  joinPinDigits.value = joinPinDigits.value.map((digit, digitIndex) =>
    digitIndex === index ? normalized : digit
  )

  if (index < PIN_LENGTH - 1) {
    void nextTick(() => focusJoinInput(index + 1))
  }
}

function handleJoinKeydown(index: number, event: KeyboardEvent): void {
  if (event.key === 'Backspace' && !joinPinDigits.value[index] && index > 0) {
    void nextTick(() => focusJoinInput(index - 1))
    return
  }

  if (event.key === 'ArrowLeft' && index > 0) {
    event.preventDefault()
    focusJoinInput(index - 1)
    return
  }

  if (event.key === 'ArrowRight' && index < PIN_LENGTH - 1) {
    event.preventDefault()
    focusJoinInput(index + 1)
  }
}

function handleJoinPaste(event: ClipboardEvent): void {
  const pasted = normalizePin(event.clipboardData?.getData('text') || '')
  if (!pasted) return
  event.preventDefault()
  applyPin(pasted)
}

function handleCloseDialog(): void {
  closeJoinDialog()
}

async function handleDismissInvite(): Promise<void> {
  clearPendingInvitePin()
  closeJoinDialog()
  if (route.params.pin) {
    await router.replace('/')
  }
}

function handleDialogClosed(): void {
  resetJoinPin()
  clearInviteState()
  isClosingAfterLeave.value = false
  closingRoomSnapshot.value = null
  closeJoinDialog()
  if (route.params.pin) {
    void router.replace('/')
  }
}

async function handleCopyRoomLink(): Promise<void> {
  const joinUrl = activeRoom.value?.joinUrl?.trim()
  if (!joinUrl) return

  try {
    await navigator.clipboard.writeText(joinUrl)
    snackbar({ message: '房间链接已复制' })
  } catch (_error) {
    snackbar({ message: '复制房间链接失败', closeable: true })
  }
}

async function handleCopyPinCode(): Promise<void> {
  const pinCode = activeRoom.value?.pinCode?.trim()
  if (!pinCode) return

  try {
    await navigator.clipboard.writeText(pinCode)
    snackbar({ message: '房间码已复制' })
  } catch (_error) {
    snackbar({ message: '复制房间码失败', closeable: true })
  }
}

watch(
  isJoinDialogOpen,
  (open) => {
    if (dialogRef.value) {
      dialogRef.value.open = open
    }

    if (open) {
      createRoomError.value = ''
      void ensureMemberIdentity().catch(() => null)
      void loadInviteRoomInfo()
      if (!isInviteMode.value) {
        void (async () => {
          let hasActiveRoom = Boolean(activeRoom.value)
          if (hasActiveRoom) {
            hasActiveRoom = await validateActiveRoom()
          }
          if (!hasActiveRoom) {
            await handleCreateRoom({ silentSuccess: true })
          }
          await nextTick()
          focusJoinInput(0)
        })()
      }
    }
  },
  { immediate: true }
)

watch(
  pendingInvitePin,
  () => {
    if (!isJoinDialogOpen.value) return
    void loadInviteRoomInfo()
  }
)

onMounted(() => {
  if (typeof window === 'undefined') return
  compactMediaQuery = window.matchMedia('(max-width: 640px)')
  syncQrCodeSize(compactMediaQuery.matches)
  compactMediaQuery.addEventListener('change', handleCompactChange)
})

onBeforeUnmount(() => {
  compactMediaQuery?.removeEventListener('change', handleCompactChange)
  compactMediaQuery = null
})
</script>

<style scoped>
.collab-join-dialog {
  padding: 1rem;
}

.collab-join-dialog:not(.invite-dialog-mode)::part(panel) {
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

.collab-join-dialog.invite-dialog-mode::part(panel) {
  width: min(92vw, 420px);
  max-width: 420px;
}

.invite-dialog-icon {
  color: rgb(var(--mdui-color-primary));
}

.invite-dialog-content {
  padding: 4px 24px 8px;
}

.invite-state {
  display: grid;
  gap: 10px;
  justify-items: start;
  color: rgb(var(--mdui-color-on-surface-variant));
}

.invite-state-ready p,
.invite-state-error {
  margin: 0;
  line-height: 1.6;
  color: rgb(var(--mdui-color-on-surface));
}

.invite-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 8px 16px 16px;
}

.dialog-shell {
  display: grid;
  max-height: min(88vh, 760px);
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  color: rgb(var(--mdui-color-on-surface));
}

.room-sheet {
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

.sheet-body,
.sheet-empty,
.sheet-loading,
.state-block {
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 20px 22px 18px;
  text-align: center;
}
.sheet-description,
.sheet-meta,
.join-hint,
.sheet-empty p {
  margin: 0;
  color: rgb(var(--mdui-color-on-surface-variant));
}
.sheet-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.qr-frame {
  display: grid;
  place-items: center;
  width: 166px;
  height: 166px;
  overflow: hidden;
  border-radius: 22px;
  background:
    linear-gradient(
      145deg,
      rgb(var(--mdui-color-surface-container-high)) 0%,
      rgb(var(--mdui-color-surface)) 100%
    );
  box-shadow:
    inset 0 0 0 1px rgb(var(--mdui-color-outline-variant) / 0.55),
    0 12px 28px rgb(var(--mdui-color-shadow) / 0.12);
}

.qr-frame :deep(.qr-canvas) {
  width: auto !important;
  height: auto !important;
  max-width: calc(100% - 20px) !important;
  max-height: calc(100% - 20px) !important;
}

.pin-code {
  margin: 0;
  font-size: clamp(2rem, 8vw, 3rem);
  letter-spacing: 0.22em;
  text-indent: 0.22em;
  line-height: 1;
  font-weight: 400;
  white-space: nowrap;
}

.pin-code-button {
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition: opacity 150ms ease, transform 150ms ease;
}

.pin-code-button:hover {
  opacity: 0.76;
}

.pin-code-button:focus-visible {
  outline: 2px solid rgb(var(--mdui-color-primary));
  outline-offset: 8px;
  border-radius: 12px;
}

.pin-code-button:active {
  transform: scale(0.98);
}

.join-sheet {
  padding: 0 22px 18px;
}

.join-divider {
  position: relative;
  display: grid;
  place-items: center;
  margin: 0 -22px;
  padding: 6px 0 0;
}

.join-divider::before {
  content: '';
  position: absolute;
  inset: 50% 0 auto;
  border-top: 1px solid rgb(var(--mdui-color-outline-variant) / 0.58);
}

.join-divider span {
  position: relative;
  z-index: 1;
  padding: 4px 12px;
  border: 1px solid rgb(var(--mdui-color-outline) / 0.55);
  border-radius: 999px;
  background: rgb(var(--mdui-color-surface));
  color: rgb(var(--mdui-color-on-surface-variant));
  font-size: 0.88rem;
}

.join-body {
  display: grid;
  justify-items: center;
  gap: 14px;
  padding-top: 18px;
  text-align: center;
}

.join-body h3,
.sheet-empty h3 {
  margin: 0;
  font-size: 1rem;
}

.pin-inputs {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  justify-content: center;
}

.pin-slot {
  display: grid;
  place-items: center;
  width: 50px;
  height: 54px;
  border-radius: 15px;
  background: rgb(var(--mdui-color-surface-container-high));
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-outline-variant) / 0.9);
  transition: transform 150ms ease, box-shadow 150ms ease, background-color 150ms ease;
}

.pin-slot[data-filled='true'] {
  background: rgb(var(--mdui-color-primary-container) / 0.5);
  box-shadow: inset 0 0 0 1px rgb(var(--mdui-color-primary) / 0.24);
}

.pin-slot:focus-within {
  transform: translateY(-1px);
  box-shadow:
    inset 0 0 0 2px rgb(var(--mdui-color-primary)),
    0 0 0 1px rgb(var(--mdui-color-primary) / 0.16);
  background: rgb(var(--mdui-color-primary-container));
}

.pin-slot input {
  width: 100%;
  height: 100%;
  border: 0;
  padding: 0;
  background: transparent;
  color: rgb(var(--mdui-color-on-surface));
  font-size: 1.45rem;
  font-weight: 600;
  text-align: center;
  text-transform: uppercase;
  outline: none;
}

.join-hint {
  width: min(100%, 19rem);
  line-height: 1.5;
  text-align: center;
}

.join-hint-error {
  color: rgb(var(--mdui-color-error));
}

.dialog-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 0 16px 16px;
}

.dialog-actions mdui-button {
  width: 100%;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 640px) {
  .collab-join-dialog {
    padding: 4px;
  }

  .collab-join-dialog:not(.invite-dialog-mode)::part(panel) {
    width: calc(100vw - 8px);
    max-width: calc(100vw - 8px);
    border-radius: 16px;
  }

  .collab-join-dialog.invite-dialog-mode::part(panel) {
    width: calc(100vw - 24px);
    max-width: calc(100vw - 24px);
  }

  .invite-dialog-content {
    padding: 2px 20px 8px;
  }

  .invite-dialog-actions {
    padding: 8px 12px 12px;
  }

  .dialog-shell {
    max-height: min(86vh, 700px);
  }

  .invite-header,
  .sheet-header {
    padding: 14px 10px 12px;
  }

  .invite-header h2,
  .sheet-header h2 {
    font-size: 1.24rem;
  }

  .sheet-body,
  .sheet-empty,
  .sheet-loading,
  .state-block,
  .invite-summary,
  .join-sheet {
    padding-left: 8px;
    padding-right: 8px;
  }

  .join-divider {
    margin-left: -8px;
    margin-right: -8px;
  }

  .qr-frame {
    width: 192px;
    height: 192px;
    border-radius: 20px;
  }

  .pin-code {
    font-size: 1.8rem;
    letter-spacing: 0.12em;
    text-indent: 0.12em;
  }

  .pin-inputs {
    gap: 5px;
  }

  .pin-slot {
    width: 39px;
    height: 43px;
    border-radius: 12px;
  }

  .pin-slot input {
    font-size: 1.08rem;
  }

  .dialog-actions {
    padding: 0 8px 10px;
  }
}
</style>
