import type { MbFileManifest } from '@/utils/mbFileDecrypt'

export class HttpStatusError extends Error {
  status: number
  response: Response

  constructor(status: number, response: Response, message?: string) {
    super(message || `HTTP ${status}`)
    this.name = 'HttpStatusError'
    this.status = status
    this.response = response
  }
}

export function buildAccessKeyQuery(accessKey?: string | null): string {
  const k = accessKey?.trim()
  if (!k) return ''
  return `?access_key=${encodeURIComponent(k)}`
}

export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, { cache: 'no-store', ...(init || {}) })
  if (!resp.ok) {
    throw new HttpStatusError(resp.status, resp)
  }
  return (await resp.json()) as T
}

export type PublicPasteInfo = {
  title: string | null
  type: 'txt' | 'md'
  status: 'published' | 'edited' | 'draft'
  published_at: string | null
  updated_at: string
  expire_at: string | null
  view_count: number
  max_views: number
}

export type PublicFileMeta = {
  paste_id: string
  file_id: string
  encrypted_name: string
  mime_type: string
  encrypted_size: number
  plain_size?: number | null
  created_at: string
  url: string
  manifest_url: string
}

export async function getPublicPasteInfo(
  pasteId: string,
  accessKey?: string | null
): Promise<PublicPasteInfo> {
  const url = `/api/pastes/${encodeURIComponent(pasteId)}${buildAccessKeyQuery(accessKey)}`
  return await fetchJson<PublicPasteInfo>(url)
}

export async function getPublicFileMeta(
  pasteId: string,
  fileId: string,
  accessKey?: string | null
): Promise<PublicFileMeta> {
  const url =
    `/api/pastes/${encodeURIComponent(pasteId)}/files/${encodeURIComponent(fileId)}/meta` +
    buildAccessKeyQuery(accessKey)
  return await fetchJson<PublicFileMeta>(url)
}

export async function getPublicFileManifest(
  pasteId: string,
  fileId: string,
  accessKey?: string | null
): Promise<MbFileManifest> {
  const url =
    `/api/pastes/${encodeURIComponent(pasteId)}/files/${encodeURIComponent(fileId)}/manifest` +
    buildAccessKeyQuery(accessKey)
  return await fetchJson<MbFileManifest>(url)
}

