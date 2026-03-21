<template>
  <mdui-dialog
    ref="dialogRef"
    class="collab-room-dialog"
    close-on-esc
    close-on-overlay-click
    @closed="handleDialogClosed"
  >
    <div class="dialog-shell">
      <section class="room-sheet">
        <header class="sheet-header">
          <p class="sheet-kicker">协作房间</p>
          <h2>{{ activeRoom?.roomName || '临时公共房间' }}</h2>
        </header>

        <div v-if="isBootstrapping" class="sheet-loading" role="status" aria-live="polite">
          <mdui-circular-progress></mdui-circular-progress>
          <span>正在准备临时公共房间…</span>
        </div>

        <div v-else-if="activeRoom" class="sheet-body">
          <div class="qr-frame">
            <QrCode :value="activeRoom.joinUrl" :size="qrCodeSize" />
          </div>

          <button
            type="button"
            class="pin-code pin-code-button"
            aria-label="点击复制当前房间码"
            @click="handleCopyPinCode"
          >
            {{ spacedPinCode }}
          </button>
          <p class="sheet-description">
            使用另一台设备扫码或输入房间码加入
          </p>
          <mdui-button variant="tonal" @click="handleCopyRoomLink">复制房间链接</mdui-button>
        </div>

        <div v-else class="sheet-error" role="alert" aria-live="polite">
          <span>{{ bootstrapError || '当前暂时无法创建临时公共房间。' }}</span>
          <mdui-button variant="tonal" @click="handleRetryBootstrap">重新生成</mdui-button>
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
          variant="text"
          :disabled="!activeRoom || isLeaving"
          :loading="isLeaving"
          @click="handleLeaveRoom"
        >
          离开
        </mdui-button>
        <mdui-button
          variant="filled"
          :disabled="!canJoin"
          :loading="isJoining"
          @click="handleJoinRoom"
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
import 'mdui/components/button.js'
import 'mdui/components/circular-progress.js'
import 'mdui/components/dialog.js'
import { snackbar } from 'mdui/functions/snackbar.js'
import QrCode from '../common/QrCode.vue'
import { useCollabDialogState } from '../../composables/useCollabDialogState'
import { useRoomSession } from '../../composables/useRoomSession'
import { getRoomInfoByPin, leaveRoom } from '../../services/rooms'

type DialogElement = HTMLElement & { open: boolean }

const PIN_LENGTH = 6

const dialogRef = ref<DialogElement | null>(null)
const joinPinDigits = ref<string[]>(Array.from({ length: PIN_LENGTH }, () => ''))
const joinInputRefs = ref<Array<HTMLInputElement | null>>(Array.from({ length: PIN_LENGTH }, () => null))
const isBootstrapping = ref(false)
const bootstrapError = ref('')
const isJoining = ref(false)
const isLeaving = ref(false)
const joinError = ref('')
const qrCodeSize = ref(152)

let compactMediaQuery: MediaQueryList | null = null

const { isCollabDialogOpen, closeCollabDialog } = useCollabDialogState()
const {
  activeRoom,
  memberIdentity,
  ensureMemberIdentity,
  createRoomAndJoin,
  joinExistingRoom,
  clearActiveRoom
} = useRoomSession()

const joinPin = computed(() => joinPinDigits.value.join(''))
const canJoin = computed(() => /^[A-Z0-9]{6}$/.test(joinPin.value) && !isJoining.value)
const spacedPinCode = computed(() => (activeRoom.value?.pinCode || '').split('').join(' '))

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

function normalizePin(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, PIN_LENGTH)
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

function applyPin(pin: string, focusLastFilled: boolean = true): void {
  const normalized = normalizePin(pin)
  const nextDigits = Array.from({ length: PIN_LENGTH }, (_, index) => normalized[index] || '')
  joinPinDigits.value = nextDigits

  const nextIndex = Math.min(normalized.length, PIN_LENGTH - 1)
  if (focusLastFilled) {
    void nextTick(() => focusJoinInput(nextIndex))
  }
}

async function ensureActiveRoom(): Promise<void> {
  if (activeRoom.value || isBootstrapping.value) return

  isBootstrapping.value = true
  bootstrapError.value = ''
  try {
    await ensureMemberIdentity()
    await createRoomAndJoin()
  } catch (error) {
    bootstrapError.value = error instanceof Error ? error.message : '创建临时公共房间失败'
  } finally {
    isBootstrapping.value = false
  }
}

async function leaveCurrentRoomMembership(): Promise<boolean> {
  const currentRoom = activeRoom.value
  if (!currentRoom) {
    clearActiveRoom()
    return true
  }

  const identity = memberIdentity.value || (await ensureMemberIdentity().catch(() => null))
  if (!identity) {
    clearActiveRoom()
    return true
  }

  try {
    await leaveRoom(identity.memberToken, currentRoom.roomId)
    clearActiveRoom()
    return true
  } catch (error) {
    snackbar({
      message: error instanceof Error ? error.message : '离开房间失败',
      closeable: true
    })
    return false
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
  closeCollabDialog()
}

function handleDialogClosed(): void {
  closeCollabDialog()
  resetJoinPin()
}

async function handleRetryBootstrap(): Promise<void> {
  await ensureActiveRoom()
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

async function handleJoinRoom(): Promise<void> {
  if (!canJoin.value) return

  isJoining.value = true
  joinError.value = ''
  try {
    const pin = joinPin.value
    const roomInfo = await getRoomInfoByPin(pin)

    if (activeRoom.value?.roomId === roomInfo.room_id) {
      snackbar({ message: '你已经在这个房间里了' })
      closeCollabDialog()
      return
    }

    if (activeRoom.value) {
      const left = await leaveCurrentRoomMembership()
      if (!left) return
    }

    await joinExistingRoom({
      roomId: roomInfo.room_id,
      roomName: roomInfo.room_name,
      pinCode: pin,
      joinUrl: `/join/${pin}`,
      memberCount: Math.min(roomInfo.member_count + 1, roomInfo.max_members),
      maxMembers: roomInfo.max_members
    })

    snackbar({ message: `已加入 ${roomInfo.room_name}` })
    resetJoinPin()
  } catch (error) {
    joinError.value = formatJoinError(error)
  } finally {
    isJoining.value = false
  }
}

async function handleLeaveRoom(): Promise<void> {
  if (!activeRoom.value || isLeaving.value) return

  isLeaving.value = true
  try {
    const left = await leaveCurrentRoomMembership()
    if (!left) return
    snackbar({ message: '已离开房间' })
    closeCollabDialog()
  } finally {
    isLeaving.value = false
  }
}

watch(
  isCollabDialogOpen,
  (open) => {
    if (dialogRef.value) {
      dialogRef.value.open = open
    }

    if (open) {
      void ensureActiveRoom()
      void nextTick(() => focusJoinInput(0))
    }
  },
  { immediate: true }
)

function syncQrCodeSize(matchesCompact: boolean): void {
  qrCodeSize.value = matchesCompact ? 176 : 152
}

function handleCompactChange(event: MediaQueryListEvent): void {
  syncQrCodeSize(event.matches)
}

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
.collab-room-dialog {
  padding: 1rem;
}

.collab-room-dialog::part(panel) {
  width: min(90vw, 500px);
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

.sheet-kicker {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgb(var(--mdui-color-secondary));
}

.sheet-header h2 {
  margin: 8px 0 0;
  font-size: 1.65rem;
  line-height: 1.1;
  color: rgb(var(--mdui-color-secondary));
}

.sheet-body,
.sheet-loading,
.sheet-error {
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 20px 22px 18px;
  text-align: center;
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

.sheet-description,
.join-hint {
  margin: 0;
}

.sheet-description,
.join-hint {
  color: rgb(var(--mdui-color-on-surface-variant));
  line-height: 1.6;
  justify-self: center;
  width: min(100%, 18rem);
  text-align: center;
}

.sheet-error {
  color: rgb(var(--mdui-color-error));
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

.join-body h3 {
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

.join-hint-error {
  color: rgb(var(--mdui-color-error));
}

.dialog-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
  .collab-room-dialog {
    padding: 4px;
  }

  .collab-room-dialog::part(panel) {
    width: calc(100vw - 8px);
    max-width: calc(100vw - 8px);
    border-radius: 16px;
  }

  .dialog-shell {
    max-height: min(86vh, 680px);
  }

  .sheet-header {
    padding: 14px 10px 12px;
  }

  .sheet-header h2 {
    font-size: 1.26rem;
  }

  .sheet-body,
  .sheet-loading,
  .sheet-error,
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

  .sheet-description,
  .join-hint {
    width: min(100%, 19rem);
    line-height: 1.5;
  }

  .dialog-actions {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    padding: 0 8px 10px;
  }
}
</style>
