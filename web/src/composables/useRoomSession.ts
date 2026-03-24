import { computed, ref, watch } from 'vue'
import axios from 'axios'
import {
  buildAbsoluteJoinUrl,
  createMemberToken,
  createRoom,
  joinRoom,
  leaveRoom,
  refreshMemberToken,
  resolveRoomWsUrl,
  type RoomInfoResponse
} from '../services/rooms'
import { strToBytes } from '../utils/crypto'
import { useAuth } from './useAuth'

const ROOM_SESSION_STORAGE_KEY = 'mb_collab_room_session'
const ROOM_SESSION_TTL_MS = 6 * 60 * 60 * 1000

export interface RoomMemberIdentity {
  memberToken: string
  displayName: string
  issuedAt: number
}

export interface ActiveRoomSession {
  roomId: string
  pinCode: string
  joinUrl: string
  roomKey: string
  wsUrl: string
  memberCount: number | null
  maxMembers: number | null
  joinedAt: number
}

interface PersistedRoomState {
  memberIdentity: RoomMemberIdentity | null
  activeRoom: ActiveRoomSession | null
}

interface ActivateRoomPayload {
  roomId: string
  pinCode: string
  joinUrl: string
  roomKey: string
  wsUrl: string
  memberCount?: number | null
  maxMembers?: number | null
}

interface UpdateActiveRoomPayload {
  pinCode?: string
  joinUrl?: string
  roomKey?: string
  wsUrl?: string
  memberCount?: number | null
  maxMembers?: number | null
}

const memberIdentity = ref<RoomMemberIdentity | null>(null)
const activeRoom = ref<ActiveRoomSession | null>(null)
const isEnsuringMemberIdentity = ref(false)
const isRefreshingMemberIdentity = ref(false)

const { currentUser } = useAuth()

let isHydrated = false
let hasBoundStorageEvents = false
let hasBoundAuthRefresh = false

function readStorage(): Storage | null {
  if (typeof window === 'undefined') return null
  return window.localStorage
}

function isStateExpired(state: PersistedRoomState | null): boolean {
  if (!state) return true
  const issuedAt = state.memberIdentity?.issuedAt ?? 0
  const joinedAt = state.activeRoom?.joinedAt ?? 0
  const newestTimestamp = Math.max(issuedAt, joinedAt)
  return newestTimestamp > 0 && Date.now() - newestTimestamp > ROOM_SESSION_TTL_MS
}

function parsePersistedState(raw: string | null): PersistedRoomState | null {
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as {
      memberIdentity?: RoomMemberIdentity | null
      activeRoom?: ActiveRoomSession | null
    }

    const nextState: PersistedRoomState = {
      memberIdentity: parsed.memberIdentity ?? null,
      activeRoom: parsed.activeRoom ?? null
    }

    if (isStateExpired(nextState)) {
      return null
    }

    return nextState
  } catch (_error) {
    return null
  }
}

function readPersistedState(): PersistedRoomState | null {
  const storage = readStorage()
  if (!storage) return null

  const nextState = parsePersistedState(storage.getItem(ROOM_SESSION_STORAGE_KEY))
  if (nextState) return nextState

  try {
    storage.removeItem(ROOM_SESSION_STORAGE_KEY)
  } catch (_error) {
    return null
  }

  return null
}

function persistState(): void {
  const storage = readStorage()
  if (!storage) return

  const payload: PersistedRoomState = {
    memberIdentity: memberIdentity.value,
    activeRoom: activeRoom.value
  }

  try {
    if (!payload.memberIdentity && !payload.activeRoom) {
      storage.removeItem(ROOM_SESSION_STORAGE_KEY)
      return
    }

    storage.setItem(ROOM_SESSION_STORAGE_KEY, JSON.stringify(payload))
  } catch (_error) {
    return
  }
}

function applyPersistedState(nextState: PersistedRoomState | null): void {
  memberIdentity.value = nextState?.memberIdentity ?? null
  activeRoom.value = nextState?.activeRoom ?? null
}

function handleStorageChange(event: StorageEvent): void {
  if (event.key !== ROOM_SESSION_STORAGE_KEY) return
  applyPersistedState(parsePersistedState(event.newValue))
}

function bindStorageEvents(): void {
  if (hasBoundStorageEvents || typeof window === 'undefined') return
  window.addEventListener('storage', handleStorageChange)
  hasBoundStorageEvents = true
}

function hydrateState(): void {
  if (isHydrated) return
  isHydrated = true
  applyPersistedState(readPersistedState())
  bindStorageEvents()
}

function setMemberIdentityState(nextIdentity: RoomMemberIdentity | null): void {
  memberIdentity.value = nextIdentity
  persistState()
}

function activateRoom(payload: ActivateRoomPayload): ActiveRoomSession {
  const nextRoom: ActiveRoomSession = {
    roomId: payload.roomId,
    pinCode: payload.pinCode.toUpperCase(),
    joinUrl: buildAbsoluteJoinUrl(payload.joinUrl),
    roomKey: payload.roomKey,
    wsUrl: resolveRoomWsUrl(payload.wsUrl),
    memberCount: payload.memberCount ?? null,
    maxMembers: payload.maxMembers ?? null,
    joinedAt: Date.now()
  }

  activeRoom.value = nextRoom
  persistState()
  return nextRoom
}

function updateActiveRoom(payload: UpdateActiveRoomPayload): void {
  hydrateState()
  if (!activeRoom.value) return

  activeRoom.value = {
    ...activeRoom.value,
    pinCode: (payload.pinCode ?? activeRoom.value.pinCode).toUpperCase(),
    joinUrl: payload.joinUrl ? buildAbsoluteJoinUrl(payload.joinUrl) : activeRoom.value.joinUrl,
    roomKey: payload.roomKey ?? activeRoom.value.roomKey,
    wsUrl: payload.wsUrl ? resolveRoomWsUrl(payload.wsUrl) : activeRoom.value.wsUrl,
    memberCount: payload.memberCount ?? activeRoom.value.memberCount,
    maxMembers: payload.maxMembers ?? activeRoom.value.maxMembers
  }

  persistState()
}

async function ensureMemberIdentity(forceRefresh: boolean = false): Promise<RoomMemberIdentity> {
  hydrateState()

  if (!forceRefresh && memberIdentity.value) {
    return memberIdentity.value
  }

  isEnsuringMemberIdentity.value = true
  try {
    const response = await createMemberToken()
    const nextIdentity: RoomMemberIdentity = {
      memberToken: response.member_token,
      displayName: response.display_name,
      issuedAt: Date.now()
    }
    setMemberIdentityState(nextIdentity)
    return nextIdentity
  } finally {
    isEnsuringMemberIdentity.value = false
  }
}

async function refreshMemberIdentity(): Promise<RoomMemberIdentity | null> {
  hydrateState()

  const currentIdentity = memberIdentity.value
  const user = currentUser.value
  if (!currentIdentity || !user) {
    return currentIdentity
  }

  const nextDisplayName = user.username.trim()
  if (!nextDisplayName || currentIdentity.displayName === nextDisplayName) {
    return currentIdentity
  }

  isRefreshingMemberIdentity.value = true
  try {
    const response = await refreshMemberToken(currentIdentity.memberToken)
    const nextIdentity: RoomMemberIdentity = {
      memberToken: response.member_token,
      displayName: response.display_name,
      issuedAt: Date.now()
    }
    setMemberIdentityState(nextIdentity)
    return nextIdentity
  } finally {
    isRefreshingMemberIdentity.value = false
  }
}

function bindAuthRefresh(): void {
  if (hasBoundAuthRefresh) return
  hasBoundAuthRefresh = true

  watch(
    () => currentUser.value?.username ?? '',
    (username) => {
      if (!username.trim()) return
      if (!memberIdentity.value) return
      if (memberIdentity.value.displayName === username.trim()) return
      void refreshMemberIdentity()
    },
    { immediate: true }
  )
}

async function createRoomAndJoin(): Promise<ActiveRoomSession> {
  const identity = await ensureMemberIdentity()
  const createdRoom = await createRoom(identity.memberToken)
  const joinedRoom = await joinRoom(identity.memberToken, createdRoom.room_id, createdRoom.pin_code)

  return activateRoom({
    roomId: createdRoom.room_id,
    pinCode: createdRoom.pin_code,
    joinUrl: createdRoom.join_url,
    roomKey: joinedRoom.room_key,
    wsUrl: joinedRoom.ws_url,
    memberCount: joinedRoom.members.length || 1,
    maxMembers: createdRoom.max_members
  })
}

async function joinExistingRoom(payload: {
  roomId: string
  pinCode: string
  joinUrl?: string
  memberCount?: number | null
  maxMembers?: number | null
}): Promise<ActiveRoomSession> {
  const identity = await ensureMemberIdentity()
  const joinedRoom = await joinRoom(identity.memberToken, payload.roomId, payload.pinCode)

  return activateRoom({
    roomId: payload.roomId,
    pinCode: payload.pinCode,
    joinUrl: payload.joinUrl ?? `/join/${payload.pinCode.toUpperCase()}`,
    roomKey: joinedRoom.room_key,
    wsUrl: joinedRoom.ws_url,
    memberCount: payload.memberCount ?? joinedRoom.members.length ?? null,
    maxMembers: payload.maxMembers ?? null
  })
}

function syncRoomInfo(roomInfo: RoomInfoResponse, pinCode: string): void {
  hydrateState()
  if (!activeRoom.value || activeRoom.value.roomId !== roomInfo.room_id) return

  updateActiveRoom({
    pinCode,
    joinUrl: `/join/${pinCode.toUpperCase()}`,
    memberCount: roomInfo.member_count,
    maxMembers: roomInfo.max_members
  })
}

async function leaveActiveRoom(): Promise<void> {
  hydrateState()
  const currentRoom = activeRoom.value
  if (!currentRoom) {
    clearActiveRoom()
    return
  }

  if (!memberIdentity.value) {
    clearActiveRoom()
    return
  }

  try {
    await leaveRoom(memberIdentity.value.memberToken, currentRoom.roomId)
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 403) {
      clearRoomState()
      return
    }

    if (axios.isAxiosError(error) && error.response?.status === 404) {
      clearActiveRoom()
      return
    }
    throw error
  }
  clearActiveRoom()
}

function clearActiveRoom(): void {
  hydrateState()
  activeRoom.value = null
  persistState()
}

function clearRoomState(): void {
  memberIdentity.value = null
  activeRoom.value = null
  persistState()
}

function requireActiveRoom(roomId?: string): ActiveRoomSession | null {
  hydrateState()
  if (!activeRoom.value) return null
  if (roomId && activeRoom.value.roomId !== roomId) return null
  return activeRoom.value
}

export function useRoomSession() {
  hydrateState()
  bindAuthRefresh()

  const roomKeyBytes = computed(() => {
    if (!activeRoom.value?.roomKey) return null
    try {
      return strToBytes(activeRoom.value.roomKey)
    } catch (_error) {
      return null
    }
  })

  return {
    memberIdentity,
    activeRoom,
    roomKeyBytes,
    isEnsuringMemberIdentity,
    isRefreshingMemberIdentity,
    ensureMemberIdentity,
    refreshMemberIdentity,
    createRoomAndJoin,
    joinExistingRoom,
    updateActiveRoom,
    syncRoomInfo,
    requireActiveRoom,
    leaveActiveRoom,
    clearActiveRoom,
    clearRoomState
  }
}
