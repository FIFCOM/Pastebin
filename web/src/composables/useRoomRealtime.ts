import { computed, ref } from 'vue'

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

interface ConnectPayload {
  roomId: string
  wsUrl: string
  memberToken: string
  onEvent?: (event: RoomRealtimeEvent) => void
}

const status = ref<RoomRealtimeStatus>('idle')
const statusMessage = ref('未连接')
const currentRoomId = ref<string | null>(null)
const selfMemberId = ref<string | null>(null)
const selfDisplayName = ref<string | null>(null)
const lastPongAt = ref<string | null>(null)

let socket: WebSocket | null = null
let keepaliveTimer: number | null = null
let currentConnectPayload: ConnectPayload | null = null
let currentEventHandler: ((event: RoomRealtimeEvent) => void) | undefined
let closedByClient = false

function clearKeepalive(): void {
  if (keepaliveTimer !== null && typeof window !== 'undefined') {
    window.clearInterval(keepaliveTimer)
  }
  keepaliveTimer = null
}

function startKeepalive(): void {
  clearKeepalive()
  if (typeof window === 'undefined') return

  keepaliveTimer = window.setInterval(() => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return
    socket.send(JSON.stringify({ type: 'ping' }))
  }, 25000)
}

function cleanupSocket(): void {
  if (socket) {
    socket.onopen = null
    socket.onmessage = null
    socket.onerror = null
    socket.onclose = null
  }
  socket = null
  clearKeepalive()
}

function emit(event: RoomRealtimeEvent): void {
  currentEventHandler?.(event)
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

async function connect(payload: ConnectPayload): Promise<void> {
  currentConnectPayload = payload
  currentEventHandler = payload.onEvent
  closedByClient = false

  disconnect(false)

  status.value = 'connecting'
  statusMessage.value = '正在连接房间…'
  currentRoomId.value = payload.roomId
  selfMemberId.value = null
  selfDisplayName.value = null
  lastPongAt.value = null

  socket = new WebSocket(payload.wsUrl)

  socket.onopen = () => {
    if (!socket) return
    socket.send(JSON.stringify({ type: 'auth', token: payload.memberToken }))
  }

  socket.onmessage = (messageEvent: MessageEvent<string>) => {
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

  socket.onerror = () => {
    if (status.value === 'connecting') {
      status.value = 'error'
      statusMessage.value = '实时连接失败'
    }
  }

  socket.onclose = (event: CloseEvent) => {
    cleanupSocket()
    if (closedByClient) {
      status.value = 'closed'
      statusMessage.value = '已断开实时连接'
      return
    }

    status.value = 'error'
    statusMessage.value = event.reason || '实时连接已断开'
  }
}

function disconnect(markClosed: boolean = true): void {
  closedByClient = markClosed
  if (socket) {
    socket.close()
  }
  cleanupSocket()
  if (markClosed) {
    status.value = 'closed'
    statusMessage.value = '已断开实时连接'
  }
}

async function reconnect(): Promise<void> {
  if (!currentConnectPayload) return
  await connect(currentConnectPayload)
}

export function useRoomRealtime() {
  const isConnected = computed(() => status.value === 'connected')

  return {
    status,
    statusMessage,
    currentRoomId,
    selfMemberId,
    selfDisplayName,
    lastPongAt,
    isConnected,
    connect,
    disconnect,
    reconnect
  }
}
