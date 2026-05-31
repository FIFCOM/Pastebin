export type ApiDocsSection = {
  slug: string
  title: string
  sidebarLabel: string
  group: string
  description: string
}

export const DOCS_BASE_PATH = '/docs'
export const DOCS_OVERVIEW_SLUG = 'overview'
export const DOCS_OVERVIEW_PATH = `${DOCS_BASE_PATH}/${DOCS_OVERVIEW_SLUG}`

export function getDocsSectionPath(slug: string): string {
  return `${DOCS_BASE_PATH}/${encodeURIComponent(slug)}`
}

export function isDocsPath(path: string): boolean {
  return path === DOCS_BASE_PATH || path.startsWith(`${DOCS_BASE_PATH}/`)
}

export const API_DOCS_SECTIONS: ApiDocsSection[] = [
  {
    slug: 'overview',
    title: 'API 文档概览',
    sidebarLabel: '概览',
    group: '入门',
    description: '了解文档范围、模块划分与阅读指南'
  },
  {
    slug: 'authentication',
    title: '认证与凭据',
    sidebarLabel: '认证与凭据',
    group: '入门',
    description: 'API Key、Paste 管理密钥、访问密码和加密密钥的区别'
  },
  {
    slug: 'paste-creation',
    title: '创建 Paste',
    sidebarLabel: '创建 Paste',
    group: 'Paste 接口',
    description: '公开 Paste 创建接口说明'
  },
  {
    slug: 'paste-files',
    title: 'Paste 内容与文件',
    sidebarLabel: '内容与文件',
    group: 'Paste 接口',
    description: 'Paste 内容、文件、读取与下载接口'
  },
  {
    slug: 'api-keys',
    title: 'API Key 可用接口',
    sidebarLabel: 'API Key 接口',
    group: '用户接口',
    description: '当前会读取用户 API Key 的协作令牌接口'
  },
  {
    slug: 'collaboration',
    title: '协作公开接口',
    sidebarLabel: '协作公开接口',
    group: '协作接口',
    description: '获取成员令牌、刷新成员令牌和查询加入信息'
  }
]

// Included endpoint families
export const INCLUDED_ENDPOINT_FAMILIES = [
  'POST /api/rooms/member-token — 获取成员令牌，可选读取 API Key',
  'POST /api/rooms/member-token/refresh — 刷新成员令牌，可选读取 API Key',
  'GET /api/join/{pin_code} — 获取房间加入信息',
  'POST /api/pastes — 公开 Paste 创建',
  'POST /api/pastes/{paste_id}/content — 内容写入',
  'POST /api/pastes/{paste_id}/files/init — 文件上传初始化',
  'GET /api/pastes/{paste_id}/files/{upload_id}/status — 上传状态',
  'PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index} — 分片上传',
  'POST /api/pastes/{paste_id}/files/{upload_id}/complete — 完成上传',
  'POST /api/pastes/{paste_id}/files/{upload_id}/abort — 中止上传',
  'DELETE /api/pastes/{paste_id}/files/{file_id} — 删除文件',
  'POST /api/pastes/{paste_id}/publish — 发布 Paste',
  'GET /api/pastes/{paste_id} — 获取 Paste 信息',
  'GET /api/pastes/{paste_id}/content — 获取 Paste 内容',
  'GET /api/pastes/{paste_id}/files/{file_id}/manifest — 文件清单',
  'GET /api/pastes/{paste_id}/files/{file_id}/meta — 文件元数据',
  'GET /api/pastes/{paste_id}/files/{file_id} — 下载文件',
  'PUT /api/pastes/{paste_id} — 更新 Paste',
  'DELETE /api/pastes/{paste_id} — 删除 Paste',
  'GET /api/config — 配置信息',
  'GET /api/docs — 默认 API 文档',
  'GET /api/docs/{slug} — 指定 API 文档'
]

// Explicit exclusions
export const EXCLUDED_ENDPOINT_FAMILIES = [
  '用户账户类接口和仅 access_token 的接口',
  '/api/user/history/* 和 /api/user/favorites/* — 用户 Paste 历史与收藏',
  '/api/internal/* — 内部接口',
  '/api/install/* — 安装引导接口',
  'POST /api/rooms — 创建房间',
  'POST /api/rooms/{room_id}/join — 加入房间',
  'GET /api/rooms/{room_id}/members — 成员列表',
  'POST /api/rooms/{room_id}/pastes — 分享 Paste 到房间',
  'GET /api/rooms/{room_id}/pastes — 房间 Paste 列表',
  'DELETE /api/rooms/{room_id}/leave — 离开房间',
  'WS /api/rooms/{room_id}/ws — 实时 WebSocket'
]

// API Key capability matrix
export type ApiKeyCapability = 'supported' | 'optional' | 'unsupported'

export type ApiKeyMatrixEntry = {
  endpoint: string
  capability: ApiKeyCapability
  credential: string
  notes: string
}

export const API_KEY_CAPABILITY_MATRIX: ApiKeyMatrixEntry[] = [
  { endpoint: 'POST /api/rooms/member-token', capability: 'optional', credential: 'Authorization: Bearer pk_...', notes: '可匿名调用；传入 API Key 时使用用户显示名' },
  { endpoint: 'POST /api/rooms/member-token/refresh', capability: 'optional', credential: 'Authorization: Bearer pk_...', notes: '需要 X-Member-Token；API Key 只用于同步显示名' },
  { endpoint: '/api/pastes/*', capability: 'unsupported', credential: 'X-Paste-Admin-Key / access_key / encryption_key', notes: 'Paste 接口使用 Paste 专用凭据' },
  { endpoint: 'GET /api/join/{pin_code}', capability: 'unsupported', credential: '无', notes: '公开查询加入信息' }
]

export function getSectionBySlug(slug: string): ApiDocsSection | undefined {
  return API_DOCS_SECTIONS.find((s) => s.slug === slug)
}

export function getValidSlugs(): string[] {
  return API_DOCS_SECTIONS.map((s) => s.slug)
}

export function getGroups(): string[] {
  const seen = new Set<string>()
  return API_DOCS_SECTIONS.filter((s) => {
    if (seen.has(s.group)) return false
    seen.add(s.group)
    return true
  }).map((s) => s.group)
}

export function getSectionsByGroup(): Map<string, ApiDocsSection[]> {
  const map = new Map<string, ApiDocsSection[]>()
  for (const section of API_DOCS_SECTIONS) {
    const group = map.get(section.group) || []
    group.push(section)
    map.set(section.group, group)
  }
  return map
}
