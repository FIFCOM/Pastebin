import axios from 'axios'
import { onBeforeUnmount, watch } from 'vue'
import { useRoomSession } from './useRoomSession'
import { useRoomRealtime } from './useRoomRealtime'
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
  const { selfMemberId, subscribe } = useRoomRealtime()

  function isRoomMissingError(error: unknown): boolean {
    return axios.isAxiosError(error) && error.response?.status === 404
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
      }
    }
  }

  const unsubscribe = subscribe((event) => {
    if (event.type === 'auth_ok' || event.type === 'member_joined' || event.type === 'member_left') {
      void refreshRoomCount()
      return
    }

    if (event.type !== 'paste_shared') return
    if (!selfMemberId.value) return
    if (event.shared_by === selfMemberId.value) return
    if (event.target_member && event.target_member !== selfMemberId.value) return
    options.onPasteShared?.(event)
  })

  watch(
    [activeRoom, memberIdentity],
    ([room, identity], [previousRoom]) => {
      if (!room || !identity) {
        return
      }

      if (previousRoom?.roomId !== room.roomId) {
        void refreshRoomCount()
      }
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
    unsubscribe()
  })

  return {
    refreshRoomCount
  }
}
