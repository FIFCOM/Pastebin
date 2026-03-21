import axios from 'axios'
import { onBeforeUnmount, watch } from 'vue'
import { useRoomSession } from './useRoomSession'
import { getRoomInfoByPin } from '../services/rooms'

type RealtimeEnvelope =
  | { type: 'auth_ok'; member_id: string }
  | { type: 'member_joined' }
  | { type: 'member_left' }
  | { type: 'pong' }
  | { type: 'paste_shared'; paste_id: string; shared_by: string; target_member: string | null; timestamp: string }
  | { type: 'error'; message?: string }

interface UseRoomPresenceSyncOptions {
  onPasteShared?: (event: Extract<RealtimeEnvelope, { type: 'paste_shared' }>) => void
}

export function useRoomPresenceSync(options: UseRoomPresenceSyncOptions = {}) {
  const { activeRoom, memberIdentity, syncRoomInfo, clearActiveRoom } = useRoomSession()

  let socket: WebSocket | null = null
  let reconnectTimer: number | null = null
  let stopped = false
  let currentRoomId = ''
  let selfMemberId = ''

  function isRoomMissingError(error: unknown): boolean {
    return axios.isAxiosError(error) && error.response?.status === 404
  }

  function clearReconnectTimer(): void {
    if (reconnectTimer !== null && typeof window !== 'undefined') {
      window.clearTimeout(reconnectTimer)
    }
    reconnectTimer = null
  }

  function cleanupSocket(): void {
    if (socket) {
      socket.onopen = null
      socket.onmessage = null
      socket.onerror = null
      socket.onclose = null
      socket.close()
    }
    socket = null
    selfMemberId = ''
  }

  async function refreshRoomCount(): Promise<void> {
    const room = activeRoom.value
    if (!room?.pinCode) return

    try {
      const info = await getRoomInfoByPin(room.pinCode)
      syncRoomInfo(info, room.pinCode)
    } catch (error) {
      if (isRoomMissingError(error)) {
        clearActiveRoom()
        cleanupSocket()
        clearReconnectTimer()
        currentRoomId = ''
      }
      return
    }
  }

  function scheduleReconnect(roomId: string): void {
    if (typeof window === 'undefined' || reconnectTimer !== null || stopped) return

    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      if (stopped) return
      if (activeRoom.value?.roomId !== roomId) return
      void connectForCurrentRoom()
    }, 3000)
  }

  async function connectForCurrentRoom(): Promise<void> {
    const room = activeRoom.value
    const identity = memberIdentity.value
    if (!room || !identity || !room.wsUrl) {
      cleanupSocket()
      return
    }

    if (socket && currentRoomId === room.roomId && socket.readyState <= WebSocket.OPEN) {
      return
    }

    clearReconnectTimer()
    cleanupSocket()
    currentRoomId = room.roomId

    const nextSocket = new WebSocket(room.wsUrl)
    socket = nextSocket

    nextSocket.onopen = () => {
      nextSocket.send(JSON.stringify({ type: 'auth', token: identity.memberToken }))
      void refreshRoomCount()
    }

    nextSocket.onmessage = (messageEvent: MessageEvent<string>) => {
      try {
        const event = JSON.parse(messageEvent.data) as RealtimeEnvelope
        if (event.type === 'auth_ok') {
          selfMemberId = event.member_id
          return
        }
        if (event.type === 'member_joined' || event.type === 'member_left') {
          void refreshRoomCount()
          return
        }
        if (event.type === 'paste_shared') {
          if (!selfMemberId) return
          if (event.shared_by === selfMemberId) return
          if (event.target_member && event.target_member !== selfMemberId) return
          options.onPasteShared?.(event)
        }
      } catch (_error) {
        return
      }
    }

    nextSocket.onerror = () => {
      return
    }

    nextSocket.onclose = () => {
      if (socket === nextSocket) {
        socket = null
      }
      if (!stopped) {
        scheduleReconnect(room.roomId)
      }
    }
  }

  function stop(): void {
    stopped = true
    clearReconnectTimer()
    cleanupSocket()
    currentRoomId = ''
  }

  watch(
    [activeRoom, memberIdentity],
    ([room, identity], [previousRoom]) => {
      if (!room || !identity) {
        cleanupSocket()
        clearReconnectTimer()
        currentRoomId = ''
        return
      }

      if (previousRoom?.roomId !== room.roomId) {
        void refreshRoomCount()
      }

      void connectForCurrentRoom()
    },
    { immediate: true }
  )

  if (typeof window !== 'undefined') {
    window.addEventListener('focus', refreshRoomCount)
  }

  onBeforeUnmount(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('focus', refreshRoomCount)
    }
    stop()
  })

  return {
    refreshRoomCount
  }
}
