import { buildAppPath } from './appUrl'

export const MB_INTERNAL_FILE_PATH_RE =
  /^\/api\/pastes\/([A-Za-z0-9_-]+)\/files\/([0-9a-fA-F-]{36})$/

export type MbInternalFileRef = {
  pasteId: string
  fileId: string
}

export function parseMbInternalFilePath(raw: string): MbInternalFileRef | null {
  if (!raw) return null

  // Accept both absolute URLs and plain paths.
  let path = raw
  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    try {
      path = new URL(raw).pathname
    } catch {
      return null
    }
  }

  const m = MB_INTERNAL_FILE_PATH_RE.exec(path)
  if (!m) return null

  const pasteId = m[1] ?? ''
  const fileId = m[2] ?? ''
  if (!pasteId || !fileId) return null

  return { pasteId, fileId }
}

export function buildMbDownloadPageHref(
  pasteId: string,
  fileId: string,
  opts?: { encryptionKeyHash?: string }
): string {
  const hash = (() => {
    const v = opts?.encryptionKeyHash ?? ''
    if (!v) return ''
    return v.startsWith('#') ? v : `#${v}`
  })()
  return `${buildAppPath(`/p/${pasteId}/download/${fileId}`)}${hash}`
}
