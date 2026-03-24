import { computed, effectScope, ref, watch } from 'vue'
import { useRoomSession } from './useRoomSession'

export type RoomRealtimeStatus = 'idle' | 'connecting' | 'connected' | 'error' | 'closed'

export interface RoomAuthOkEvent {
  type: 'auth_ok'
  room_id: string
  member_id: string
  display_name: string
  timestamp: string
}

export interface RoomMemberJoinedEvent {
  type: 'member_joined'
  member_id: string
  display_name: string
  timestamp: string
}

export interface RoomMemberLeftEvent {
  type: 'member_left'
  member_id: string
  display_name: string
  timestamp: string
}

export interface RoomPasteSharedEvent {
  type: 'paste_shared'
  paste_id: string
  shared_by: string
  target_member: string | null
  timestamp: string
}

export interface RoomPongEvent {
  type: 'pong'
  timestamp: string
}

export interface RoomErrorEvent {
  type: 'error'
  message: string
}

export type RoomRealtimeEvent =
  | RoomAuthOkEvent
  | RoomMemberJoinedEvent
  | RoomMemberLeftEvent
  | RoomPasteSharedEvent
  | RoomPongEvent
  | RoomErrorEvent

interface ConnectionTarget {
  roomId: string
  wsUrl: string
  memberToken: string
}

type RoomRealtimeListener = (event: RoomRealtimeEvent) => void

const status = ref<RoomRealtimeStatus>('idle')
const statusMessage = ref('未连接')
const currentRoomId = ref<string | null>(null)
const selfMemberId = ref<string | null>(null)
const selfDisplayName = ref<string | null>(null)
const lastPongAt = ref<string | null>(null)

const listeners = new Set<RoomRealtimeListener>()

let socket: WebSocket | null = null
let keepaliveTimer: number | null = null
let reconnectTimer: number | null = null
let currentTarget: ConnectionTarget | null = null
let closedByClient = false
let hasBoundSessionWatcher = false

function clearKeepalive(): void {
  if (keepaliveTimer !== null && typeof window !== 'undefined') {
    window.clearInterval(keepaliveTimer)
  }
  keepaliveTimer = null
}

function clearReconnectTimer(): void {
  if (reconnectTimer !== null && typeof window !== 'undefined') {
    window.clearTimeout(reconnectTimer)
  }
  reconnectTimer = null
}

function startKeepalive(): void {
  clearKeepalive()
  if (typeof window === 'undefined') return

  keepaliveTimer = window.setInterval(() => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return
    socket.send(JSON.stringify({ type: 'ping' }))
  }, 25000)
}

function detachSocket(targetSocket: WebSocket | null): void {
  if (!targetSocket) return
  targetSocket.onopen = null
  targetSocket.onmessage = null
  targetSocket.onerror = null
  targetSocket.onclose = null
}

function disposeSocket(targetSocket: WebSocket | null = socket): void {
  if (!targetSocket) return

  const isActiveSocket = socket === targetSocket
  detachSocket(targetSocket)

  if (isActiveSocket) {
    socket = null
    clearKeepalive()
  }

  if (targetSocket.readyState === WebSocket.CONNECTING || targetSocket.readyState === WebSocket.OPEN) {
    targetSocket.close()
  }
}

function resetConnectionState(nextStatus: RoomRealtimeStatus = 'idle', nextMessage: string = '未连接'): void {
  disposeSocket()
  clearReconnectTimer()
  currentRoomId.value = null
  selfMemberId.value = null
  selfDisplayName.value = null
  lastPongAt.value = null
  status.value = nextStatus
  statusMessage.value = nextMessage
}

function emit(event: RoomRealtimeEvent): void {
  listeners.forEach((listener) => {
    listener(event)
  })
}

function handleRealtimeEvent(event: RoomRealtimeEvent): void {
  if (event.type === 'auth_ok') {
    selfMemberId.value = event.member_id
    selfDisplayName.value = event.display_name
    status.value = 'connected'
    statusMessage.value = '实时连接已建立'
    startKeepalive()
  } else if (event.type === 'pong') {
    lastPongAt.value = event.timestamp
  } else if (event.type === 'error') {
    status.value = 'error'
    statusMessage.value = event.message
  }

  emit(event)
}

function scheduleReconnect(): void {
  if (typeof window === 'undefined' || reconnectTimer !== null || !currentTarget) return

  const targetSnapshot = currentTarget
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null
    if (!currentTarget) return
    if (
      currentTarget.roomId !== targetSnapshot.roomId ||
      currentTarget.wsUrl !== targetSnapshot.wsUrl ||
      currentTarget.memberToken !== targetSnapshot.memberToken
    ) {
      return
    }
    connectToTarget(targetSnapshot)
  }, 3000)
}

function connectToTarget(target: ConnectionTarget): void {
  const hasLiveSocket =
    socket !== null &&
    currentRoomId.value === target.roomId &&
    currentTarget?.wsUrl === target.wsUrl &&
    currentTarget.memberToken === target.memberToken &&
    socket.readyState <= WebSocket.OPEN

  currentTarget = target
  closedByClient = false

  if (hasLiveSocket) {
    return
  }

  clearReconnectTimer()
  disposeSocket()

  status.value = 'connecting'
  statusMessage.value = '正在连接房间…'
  currentRoomId.value = target.roomId
  selfMemberId.value = null
  selfDisplayName.value = null
  lastPongAt.value = null

  const nextSocket = new WebSocket(target.wsUrl)
  socket = nextSocket

  nextSocket.onopen = () => {
    if (socket !== nextSocket) return
    nextSocket.send(JSON.stringify({ type: 'auth', token: target.memberToken }))
  }

  nextSocket.onmessage = (messageEvent: MessageEvent<string>) => {
    if (socket !== nextSocket) return
    try {
      const parsed = JSON.parse(messageEvent.data) as RoomRealtimeEvent
      if (!parsed || typeof parsed !== 'object' || typeof parsed.type !== 'string') {
        throw new Error('invalid event')
      }
      handleRealtimeEvent(parsed)
    } catch {
      status.value = 'error'
      statusMessage.value = '实时消息解析失败'
    }
  }

  nextSocket.onerror = () => {
    if (socket !== nextSocket) return
    if (status.value === 'connecting') {
      status.value = 'error'
      statusMessage.value = '实时连接失败'
    }
  }

  nextSocket.onclose = (event: CloseEvent) => {
    if (socket !== nextSocket) return

    if (socket === nextSocket) {
      disposeSocket(nextSocket)
    }

    if (closedByClient) {
      status.value = currentTarget ? 'closed' : 'idle'
      statusMessage.value = currentTarget ? '已断开实时连接' : '未连接'
      return
    }

    status.value = 'error'
    statusMessage.value = event.reason || '实时连接已断开'
    scheduleReconnect()
  }
}

function syncConnectionTarget(): void {
  const { activeRoom, memberIdentity } = useRoomSession()
  const room = activeRoom.value
  const identity = memberIdentity.value

  if (!room || !identity || !room.wsUrl) {
    currentTarget = null
    closedByClient = true
    resetConnectionState()
    return
  }

  connectToTarget({
    roomId: room.roomId,
    wsUrl: room.wsUrl,
    memberToken: identity.memberToken
  })
}

function bindSessionLifecycle(): void {
  if (hasBoundSessionWatcher) return
  hasBoundSessionWatcher = true

  effectScope(true).run(() => {
    const { activeRoom, memberIdentity } = useRoomSession()
    watch([activeRoom, memberIdentity], () => {
      syncConnectionTarget()
    }, { immediate: true })
  })
}

function subscribe(listener: RoomRealtimeListener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useRoomRealtime() {
  bindSessionLifecycle()

  const isConnected = computed(() => status.value === 'connected')

  return {
    status,
    statusMessage,
    currentRoomId,
    selfMemberId,
    selfDisplayName,
    lastPongAt,
    isConnected,
    subscribe
  }
}
