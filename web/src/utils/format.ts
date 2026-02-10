export function humanSize(bytes: number): string {
  const n = Number(bytes)
  if (!Number.isFinite(n) || n < 0) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB', 'TB'] as const
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }

  const unit = units[i] ?? 'B'
  const fixed = i === 0 ? v.toFixed(0) : v.toFixed(v >= 10 ? 1 : 2)
  return `${fixed} ${unit}`
}

export function formatDateTime(raw?: string | number | Date | null, fallback: string = '-'): string {
  if (raw === null || raw === undefined || raw === '') return fallback
  const d = raw instanceof Date ? raw : new Date(raw)
  return Number.isNaN(d.getTime()) ? String(raw) : d.toLocaleString()
}

export function formatDate(raw?: string | number | Date | null, fallback: string = '-'): string {
  if (raw === null || raw === undefined || raw === '') return fallback
  const d = raw instanceof Date ? raw : new Date(raw)
  return Number.isNaN(d.getTime()) ? String(raw) : d.toLocaleDateString()
}

export function formatDurationSeconds(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = s % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
  return `${m}:${String(ss).padStart(2, '0')}`
}

