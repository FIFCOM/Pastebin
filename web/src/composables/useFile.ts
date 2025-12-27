const IMAGE_FILE_EXTENSIONS = [
  'png',
  'jpg',
  'jpeg',
  'gif',
  'webp',
  'bmp',
  'svg',
  'ico',
  'tif',
  'tiff',
  'avif'
] as const

export function isImageFileName(fileName: string): boolean {
  if (!fileName) return false

  const base = fileName.split(/[?#]/, 1)[0] ?? ''
  const nameOnly = base.split('/').pop() ?? base

  const lastDot = nameOnly.lastIndexOf('.')
  if (lastDot <= 0) return false

  const ext = nameOnly.slice(lastDot + 1).toLowerCase()
  if (!ext) return false

  return IMAGE_FILE_EXTENSIONS.includes(ext as (typeof IMAGE_FILE_EXTENSIONS)[number])
}

