function matchFirst(raw: string, patterns: RegExp[]): string | null {
  for (const pattern of patterns) {
    const found = raw.match(pattern)
    if (found?.[1]) return found[1]
  }
  return null
}

export function getDeviceLabel(userAgent: string | null | undefined): string {
  const ua = (userAgent ?? '').trim()
  if (!ua) return '未知设备'

  const browser = (() => {
    if (/Edg\//i.test(ua)) return `Edge ${matchFirst(ua, [/Edg\/(\d+(?:\.\d+)?)/i]) ?? ''}`.trim()
    if (/Chrome\//i.test(ua) && !/Edg\//i.test(ua)) {
      return `Chrome ${matchFirst(ua, [/Chrome\/(\d+(?:\.\d+)?)/i]) ?? ''}`.trim()
    }
    if (/Firefox\//i.test(ua)) {
      return `Firefox ${matchFirst(ua, [/Firefox\/(\d+(?:\.\d+)?)/i]) ?? ''}`.trim()
    }
    if (/Safari\//i.test(ua) && /Version\//i.test(ua) && !/Chrome\//i.test(ua)) {
      return `Safari ${matchFirst(ua, [/Version\/(\d+(?:\.\d+)?)/i]) ?? ''}`.trim()
    }
    return '浏览器'
  })()

  const os = (() => {
    if (/Windows NT/i.test(ua)) return 'Windows'
    if (/Android/i.test(ua)) return 'Android'
    if (/iPhone|iPad|iPod/i.test(ua)) return 'iOS'
    if (/Mac OS X/i.test(ua)) return 'macOS'
    if (/Linux/i.test(ua)) return 'Linux'
    return '未知系统'
  })()

  return `${browser} · ${os}`
}
