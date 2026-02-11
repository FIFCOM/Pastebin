function getFileExt(name: string): string {
  const base = (name || '').trim()
  const idx = base.lastIndexOf('.')
  if (idx <= 0 || idx >= base.length - 1) return ''
  return base.slice(idx + 1).toLowerCase()
}

export function isProbablyText(mime: string, name: string): boolean {
  const mt = (mime || '').toLowerCase().trim()
  if (mt.startsWith('text/')) return true
  if (
    mt === 'application/json' ||
    mt === 'application/xml' ||
    mt === 'application/yaml' ||
    mt === 'application/x-yaml' ||
    mt === 'application/toml'
  ) {
    return true
  }

  const ext = getFileExt(name)
  return (
    ext === 'txt' ||
    ext === 'md' ||
    ext === 'json' ||
    ext === 'csv' ||
    ext === 'log' ||
    ext === 'yaml' ||
    ext === 'yml' ||
    ext === 'toml' ||
    ext === 'ini' ||
    ext === 'conf' ||
    ext === 'xml'
  )
}

export function fileTypeToIconName(mime: string, name: string): string {
  const mt = (mime || '').toLowerCase().trim()
  const ext = getFileExt(name)

  if (
    mt.startsWith('image/') ||
    ext === 'jpg' ||
    ext === 'jpeg' ||
    ext === 'png' ||
    ext === 'gif' ||
    ext === 'webp' ||
    ext === 'bmp' ||
    ext === 'svg' ||
    ext === 'ico' ||
    ext === 'tif' ||
    ext === 'tiff' ||
    ext === 'avif' ||
    ext === 'heic'
  ) {
    return 'image'
  }

  if (
    mt.startsWith('audio/') ||
    ext === 'mp3' ||
    ext === 'wav' ||
    ext === 'flac' ||
    ext === 'aac' ||
    ext === 'ogg' ||
    ext === 'm4a' ||
    ext === 'wma' ||
    ext === 'opus' ||
    ext === 'amr' ||
    ext === 'mid' ||
    ext === 'midi'
  ) {
    return 'music_note'
  }

  if (
    mt.startsWith('video/') ||
    ext === 'mp4' ||
    ext === 'mkv' ||
    ext === 'mov' ||
    ext === 'avi' ||
    ext === 'webm' ||
    ext === 'flv' ||
    ext === 'wmv' ||
    ext === 'm4v' ||
    ext === '3gp' ||
    ext === 'ts'
  ) {
    return 'movie'
  }

  // PDF
  if (mt === 'application/pdf' || ext === 'pdf') return 'picture_as_pdf'

  // Archives / compressed files
  if (
    mt === 'application/zip' ||
    mt === 'application/x-7z-compressed' ||
    mt === 'application/x-rar-compressed' ||
    mt === 'application/vnd.rar' ||
    mt === 'application/x-tar' ||
    mt === 'application/gzip' ||
    mt === 'application/x-gzip' ||
    mt === 'application/x-bzip2' ||
    mt === 'application/x-xz' ||
    mt === 'application/zstd' ||
    ext === 'zip' ||
    ext === 'rar' ||
    ext === '7z' ||
    ext === 'tar' ||
    ext === 'gz' ||
    ext === 'tgz' ||
    ext === 'bz2' ||
    ext === 'xz' ||
    ext === 'zst' ||
    ext === 'lz' ||
    ext === 'lz4'
  ) {
    return 'folder_zip'
  }

  // Office docs / documents
  if (
    mt === 'application/msword' ||
    mt === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    mt === 'application/vnd.oasis.opendocument.text' ||
    ext === 'doc' ||
    ext === 'docx' ||
    ext === 'odt' ||
    ext === 'wps' ||
    ext === 'pages'
  ) {
    return 'description'
  }

  // Spreadsheets
  if (
    mt === 'application/vnd.ms-excel' ||
    mt === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    mt === 'application/vnd.oasis.opendocument.spreadsheet' ||
    ext === 'xls' ||
    ext === 'xlsx' ||
    ext === 'ods' ||
    ext === 'numbers'
  ) {
    return 'table_chart'
  }

  // Presentations
  if (
    mt === 'application/vnd.ms-powerpoint' ||
    mt === 'application/vnd.openxmlformats-officedocument.presentationml.presentation' ||
    mt === 'application/vnd.oasis.opendocument.presentation' ||
    ext === 'ppt' ||
    ext === 'pptx' ||
    ext === 'odp' ||
    ext === 'key'
  ) {
    return 'slideshow'
  }

  // Source / config / script
  if (
    ext === 'ts' ||
    ext === 'tsx' ||
    ext === 'js' ||
    ext === 'jsx' ||
    ext === 'c' ||
    ext === 'h' ||
    ext === 'cpp' ||
    ext === 'hpp' ||
    ext === 'rs' ||
    ext === 'go' ||
    ext === 'java' ||
    ext === 'py' ||
    ext === 'php' ||
    ext === 'rb' ||
    ext === 'sh' ||
    ext === 'bash' ||
    ext === 'zsh' ||
    ext === 'sql' ||
    ext === 'vue' ||
    ext === 'css' ||
    ext === 'scss' ||
    ext === 'html'
  ) {
    return 'code'
  }

  // Fonts
  if (
    mt.startsWith('font/') ||
    mt === 'application/font-woff' ||
    mt === 'application/font-woff2' ||
    ext === 'ttf' ||
    ext === 'otf' ||
    ext === 'woff' ||
    ext === 'woff2'
  ) {
    return 'font_download'
  }

  return 'insert_drive_file'
}
