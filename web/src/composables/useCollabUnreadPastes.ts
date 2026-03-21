import { computed, ref } from 'vue'

const unreadPasteKeysByRoom = ref<Record<string, string[]>>({})

function normalizeRoomId(roomId: unknown): string {
  return typeof roomId === 'string' ? roomId.trim() : ''
}

function normalizeEntryKey(entryKey: unknown): string {
  return typeof entryKey === 'string' ? entryKey.trim() : ''
}

export function buildUnreadPasteKey(pasteId: string, timestamp: string): string {
  return `${pasteId.trim()}::${timestamp.trim()}`
}

function uniqueKeys(keys: string[]): string[] {
  return Array.from(new Set(keys.filter(Boolean)))
}

export function useCollabUnreadPastes() {
  function markUnreadPaste(roomId: unknown, entryKey: unknown): void {
    const normalizedRoomId = normalizeRoomId(roomId)
    const normalizedEntryKey = normalizeEntryKey(entryKey)
    if (!normalizedRoomId || !normalizedEntryKey) return

    const currentKeys = unreadPasteKeysByRoom.value[normalizedRoomId] ?? []
    unreadPasteKeysByRoom.value = {
      ...unreadPasteKeysByRoom.value,
      [normalizedRoomId]: uniqueKeys([normalizedEntryKey, ...currentKeys])
    }
  }

  function clearUnreadPaste(roomId: unknown, entryKey: unknown): void {
    const normalizedRoomId = normalizeRoomId(roomId)
    const normalizedEntryKey = normalizeEntryKey(entryKey)
    if (!normalizedRoomId || !normalizedEntryKey) return

    const currentKeys = unreadPasteKeysByRoom.value[normalizedRoomId] ?? []
    const nextKeys = currentKeys.filter((key) => key !== normalizedEntryKey)
    unreadPasteKeysByRoom.value = {
      ...unreadPasteKeysByRoom.value,
      [normalizedRoomId]: nextKeys
    }
  }

  function clearUnreadPastes(roomId: unknown, entryKeys?: string[]): void {
    const normalizedRoomId = normalizeRoomId(roomId)
    if (!normalizedRoomId) return

    if (!entryKeys?.length) {
      unreadPasteKeysByRoom.value = {
        ...unreadPasteKeysByRoom.value,
        [normalizedRoomId]: []
      }
      return
    }

    const nextRemovalSet = new Set(entryKeys.map(normalizeEntryKey).filter(Boolean))
    const currentKeys = unreadPasteKeysByRoom.value[normalizedRoomId] ?? []
    unreadPasteKeysByRoom.value = {
      ...unreadPasteKeysByRoom.value,
      [normalizedRoomId]: currentKeys.filter((key) => !nextRemovalSet.has(key))
    }
  }

  function clearRoomUnreadState(roomId: unknown): void {
    const normalizedRoomId = normalizeRoomId(roomId)
    if (!normalizedRoomId) return

    const nextState = { ...unreadPasteKeysByRoom.value }
    delete nextState[normalizedRoomId]
    unreadPasteKeysByRoom.value = nextState
  }

  function unreadKeysForRoom(roomId: unknown): string[] {
    const normalizedRoomId = normalizeRoomId(roomId)
    if (!normalizedRoomId) return []
    return unreadPasteKeysByRoom.value[normalizedRoomId] ?? []
  }

  function hasUnreadPastes(roomId: unknown): boolean {
    return unreadKeysForRoom(roomId).length > 0
  }

  function useRoomUnreadKeys(roomId: { value: string | null | undefined }) {
    return computed(() => unreadKeysForRoom(roomId.value))
  }

  return {
    unreadPasteKeysByRoom,
    markUnreadPaste,
    clearUnreadPaste,
    clearUnreadPastes,
    clearRoomUnreadState,
    unreadKeysForRoom,
    hasUnreadPastes,
    useRoomUnreadKeys
  }
}
