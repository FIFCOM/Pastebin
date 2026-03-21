import { computed, ref } from 'vue'
import {
  buildAbsoluteJoinUrl,
  createMemberToken,
  createRoom,
  joinRoom,
  resolveRoomWsUrl,
  type RoomInfoResponse
} from '../services/rooms'
import { strToBytes } from '../utils/crypto'

const ROOM_SESSION_STORAGE_KEY = 'mb_collab_room_session_v1'
const ROOM_SESSION_TTL_MS = 6 * 60 * 60 * 1000

export interface RoomMemberIdentity {
  memberToken: string
  displayName: string
  issuedAt: number
}

export interface ActiveRoomSession {
  roomId: string
  roomName: string
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
  roomName: string
  pinCode: string
  joinUrl: string
  roomKey: string
  wsUrl: string
  memberCount?: number | null
  maxMembers?: number | null
}

const memberIdentity = ref<RoomMemberIdentity | null>(null)
const activeRoom = ref<ActiveRoomSession | null>(null)
const isEnsuringMemberIdentity = ref(false)
let isHydrated = false

function readPersistedState(): PersistedRoomState | null {
  if (typeof window === 'undefined') return null

  try {
    const raw = sessionStorage.getItem(ROOM_SESSION_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as {
      memberIdentity?: RoomMemberIdentity | null
      activeRoom?: ActiveRoomSession | null
    }
    const nextState: PersistedRoomState = {
      memberIdentity: parsed.memberIdentity ?? null,
      activeRoom: parsed.activeRoom ?? null
    }

    const issuedAt = nextState.memberIdentity?.issuedAt ?? 0
    const joinedAt = nextState.activeRoom?.joinedAt ?? 0
    const newestTimestamp = Math.max(issuedAt, joinedAt)
    if (newestTimestamp > 0 && Date.now() - newestTimestamp > ROOM_SESSION_TTL_MS) {
      sessionStorage.removeItem(ROOM_SESSION_STORAGE_KEY)
      return null
    }

    return nextState
  } catch (_error) {
    return null
  }
}

function persistState(): void {
  if (typeof window === 'undefined') return

  const payload: PersistedRoomState = {
    memberIdentity: memberIdentity.value,
    activeRoom: activeRoom.value
  }

  try {
    sessionStorage.setItem(ROOM_SESSION_STORAGE_KEY, JSON.stringify(payload))
  } catch (_error) {
    return
  }
}

function hydrateState(): void {
  if (isHydrated) return
  isHydrated = true

  const persisted = readPersistedState()
  if (!persisted) return

  memberIdentity.value = persisted.memberIdentity
  activeRoom.value = persisted.activeRoom
}

function setMemberIdentityState(nextIdentity: RoomMemberIdentity | null): void {
  memberIdentity.value = nextIdentity
  persistState()
}

function activateRoom(payload: ActivateRoomPayload): ActiveRoomSession {
  const nextRoom: ActiveRoomSession = {
    roomId: payload.roomId,
    roomName: payload.roomName,
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

async function createRoomAndJoin(): Promise<ActiveRoomSession> {
  const identity = await ensureMemberIdentity()
  const createdRoom = await createRoom(identity.memberToken)
  const joinedRoom = await joinRoom(identity.memberToken, createdRoom.room_id, createdRoom.pin_code)

  return activateRoom({
    roomId: createdRoom.room_id,
    roomName: createdRoom.room_name,
    pinCode: createdRoom.pin_code,
    joinUrl: createdRoom.join_url,
    roomKey: joinedRoom.room_key,
    wsUrl: joinedRoom.ws_url,
    memberCount: 1,
    maxMembers: createdRoom.max_members
  })
}

async function joinExistingRoom(payload: {
  roomId: string
  pinCode: string
  roomName: string
  joinUrl?: string
  memberCount?: number | null
  maxMembers?: number | null
}): Promise<ActiveRoomSession> {
  const identity = await ensureMemberIdentity()
  const joinedRoom = await joinRoom(identity.memberToken, payload.roomId, payload.pinCode)

  return activateRoom({
    roomId: payload.roomId,
    roomName: payload.roomName,
    pinCode: payload.pinCode,
    joinUrl: payload.joinUrl ?? `/join/${payload.pinCode.toUpperCase()}`,
    roomKey: joinedRoom.room_key,
    wsUrl: joinedRoom.ws_url,
    memberCount: payload.memberCount ?? null,
    maxMembers: payload.maxMembers ?? null
  })
}

function syncRoomInfo(roomInfo: RoomInfoResponse, pinCode: string): void {
  hydrateState()
  if (!activeRoom.value || activeRoom.value.roomId !== roomInfo.room_id) return

  activeRoom.value = {
    ...activeRoom.value,
    roomName: roomInfo.room_name,
    pinCode: pinCode.toUpperCase(),
    joinUrl: buildAbsoluteJoinUrl(`/join/${pinCode.toUpperCase()}`),
    memberCount: roomInfo.member_count,
    maxMembers: roomInfo.max_members
  }
  persistState()
}

function clearActiveRoom(): void {
  hydrateState()
  activeRoom.value = null
  persistState()
}

function clearRoomState(): void {
  memberIdentity.value = null
  activeRoom.value = null
  if (typeof window !== 'undefined') {
    try {
      sessionStorage.removeItem(ROOM_SESSION_STORAGE_KEY)
    } catch (_error) {
      return
    }
  }
}

function requireActiveRoom(roomId?: string): ActiveRoomSession | null {
  hydrateState()
  if (!activeRoom.value) return null
  if (roomId && activeRoom.value.roomId !== roomId) return null
  return activeRoom.value
}

export function useRoomSession() {
  hydrateState()

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
    ensureMemberIdentity,
    createRoomAndJoin,
    joinExistingRoom,
    syncRoomInfo,
    requireActiveRoom,
    clearActiveRoom,
    clearRoomState
  }
}
