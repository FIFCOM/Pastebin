function normalizeAppBasePath(): string {
  const rawBasePath = String(import.meta.env.BASE_URL || '/').trim()
  if (!rawBasePath || rawBasePath === '/') return '/'

  const withLeadingSlash = rawBasePath.startsWith('/') ? rawBasePath : `/${rawBasePath}`
  return withLeadingSlash.endsWith('/') ? withLeadingSlash : `${withLeadingSlash}/`
}

export function buildAppPath(pathname: string): string {
  const normalizedPath = pathname.trim()
  if (!normalizedPath.startsWith('/')) return normalizedPath

  const basePath = normalizeAppBasePath()
  if (basePath === '/') return normalizedPath

  const basePathWithoutTrailingSlash = basePath.slice(0, -1)
  if (
    normalizedPath === basePathWithoutTrailingSlash ||
    normalizedPath.startsWith(`${basePath}`)
  ) {
    return normalizedPath
  }

  return `${basePathWithoutTrailingSlash}${normalizedPath}`
}

export function buildAbsoluteAppUrl(pathOrUrl: string): string {
  if (typeof window === 'undefined') return pathOrUrl

  const normalized = pathOrUrl.trim()
  if (!normalized) return normalized

  const looksAbsoluteUrl = /^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(normalized)
  if (looksAbsoluteUrl) {
    try {
      return new URL(normalized).toString()
    } catch (_error) {
      return normalized
    }
  }

  try {
    const baseUrl = new URL(normalizeAppBasePath(), window.location.origin)
    const resolvedPath = normalized.startsWith('/') ? buildAppPath(normalized) : normalized
    return new URL(resolvedPath, baseUrl).toString()
  } catch (_error) {
    return normalized
  }
}
