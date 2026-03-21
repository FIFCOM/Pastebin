import { apiHttp } from './http'
import { buildAbsoluteAppUrl } from '../utils/appUrl'

export type RoomPasteFilter = 'received' | 'sent' | 'all'

export interface MemberTokenResponse {
  member_token: string
  display_name: string
}

export interface CreateRoomRequest {}

export interface CreateRoomResponse {
  room_id: string
  pin_code: string
  join_url: string
  max_members: number
}

export interface RoomInfoResponse {
  room_id: string
  member_count: number
  max_members: number
}

export interface JoinedRoomMember {
  id: string
  display_name: string
  joined_at: string
}

export interface JoinRoomResponse {
  room_key: string
  members: JoinedRoomMember[]
  ws_url: string
}

export interface RoomMember {
  member_id: string
  display_name: string
  last_seen: string
  is_online: boolean
  joined_at: string
}

export interface RoomMembersResponse {
  members: RoomMember[]
}

export interface SharedPasteRecord {
  paste_id: string
  title: string | null
  encrypted_paste_key: string
  encrypted_admin_key: string | null
  shared_by: string
  target_member: string | null
  shared_at: string
  expire_at: string | null
  is_expired: boolean
}

export interface RoomPastesResponse {
  pastes: SharedPasteRecord[]
}

export interface SharePasteRequest {
  paste_id: string
  encrypted_paste_key: string
  encrypted_admin_key?: string
  target_member_id?: string
}

function memberAuthHeaders(memberToken: string) {
  return {
    headers: {
      Authorization: `Bearer ${memberToken}`
    }
  }
}

function websocketOriginFromRuntimeConfig(): string {
  if (typeof window === 'undefined') return ''

  const runtimeCandidates = [
    import.meta.env.VITE_API_BASE_URL as string | undefined,
    import.meta.env.VITE_BACKEND as string | undefined
  ]

  for (const candidate of runtimeCandidates) {
    const normalized = candidate?.trim()
    if (!normalized) continue

    try {
      const url = new URL(normalized, window.location.origin)
      if (url.protocol === 'http:' || url.protocol === 'https:') {
        const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
        return `${protocol}//${url.host}`
      }
    } catch (_error) {
      continue
    }
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

export function buildAbsoluteJoinUrl(joinUrl: string): string {
  return buildAbsoluteAppUrl(joinUrl)
}

export function resolveRoomWsUrl(wsUrl: string): string {
  if (typeof window === 'undefined') return wsUrl

  const normalized = wsUrl.trim()
  if (!normalized) return normalized

  try {
    const base = websocketOriginFromRuntimeConfig() || window.location.origin
    const url = new URL(normalized, base)
    if (url.protocol === 'http:' || url.protocol === 'https:') {
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    }
    return url.toString()
  } catch (_error) {
    return normalized
  }
}

export async function createMemberToken(): Promise<MemberTokenResponse> {
  const response = await apiHttp.post<MemberTokenResponse>('/rooms/member-token')
  return response.data
}

export async function refreshMemberToken(memberToken: string): Promise<MemberTokenResponse> {
  const response = await apiHttp.post<MemberTokenResponse>('/rooms/member-token/refresh', null, {
    headers: {
      'X-Member-Token': memberToken
    }
  })
  return response.data
}

export async function createRoom(
  memberToken: string,
  payload: CreateRoomRequest = {}
): Promise<CreateRoomResponse> {
  const response = await apiHttp.post<CreateRoomResponse>('/rooms', payload, memberAuthHeaders(memberToken))
  return response.data
}

export async function getRoomInfoByPin(pinCode: string): Promise<RoomInfoResponse> {
  const response = await apiHttp.get<RoomInfoResponse>(`/join/${encodeURIComponent(pinCode)}`)
  return response.data
}

export async function joinRoom(
  memberToken: string,
  roomId: string,
  pinCode: string
): Promise<JoinRoomResponse> {
  const response = await apiHttp.post<JoinRoomResponse>(
    `/rooms/${encodeURIComponent(roomId)}/join`,
    { pin_code: pinCode },
    memberAuthHeaders(memberToken)
  )
  return response.data
}

export async function getRoomMembers(memberToken: string, roomId: string): Promise<RoomMembersResponse> {
  const response = await apiHttp.get<RoomMembersResponse>(
    `/rooms/${encodeURIComponent(roomId)}/members`,
    memberAuthHeaders(memberToken)
  )
  return response.data
}

export async function getRoomPastes(
  memberToken: string,
  roomId: string,
  type: RoomPasteFilter
): Promise<RoomPastesResponse> {
  const response = await apiHttp.get<RoomPastesResponse>(`/rooms/${encodeURIComponent(roomId)}/pastes`, {
    ...memberAuthHeaders(memberToken),
    params: { type }
  })
  return response.data
}

export async function sharePasteToRoom(
  memberToken: string,
  roomId: string,
  payload: SharePasteRequest
): Promise<void> {
  await apiHttp.post(`/rooms/${encodeURIComponent(roomId)}/pastes`, payload, memberAuthHeaders(memberToken))
}

export async function leaveRoom(memberToken: string, roomId: string): Promise<void> {
  await apiHttp.delete(`/rooms/${encodeURIComponent(roomId)}/leave`, memberAuthHeaders(memberToken))
}
