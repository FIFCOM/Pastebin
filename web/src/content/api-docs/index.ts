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
    title: '认证方式',
    sidebarLabel: '认证方式',
    group: '入门',
    description: 'API Key、Access Token 等各种认证方式的说明'
  },
  {
    slug: 'paste-creation',
    title: '创建 Paste',
    sidebarLabel: '创建 Paste',
    group: 'Paste 接口',
    description: '公开 Paste 创建接口说明'
  },
  {
    slug: 'pastes-files',
    title: 'Paste 内容与文件管理',
    sidebarLabel: '内容与文件',
    group: 'Paste 接口',
    description: 'Paste 内容、文件上传、发布与管理的完整接口'
  },
  {
    slug: 'account-security',
    title: '账户与安全',
    sidebarLabel: '账户与安全',
    group: '用户接口',
    description: '用户信息、会话管理、TOTP 两步验证等接口'
  },
  {
    slug: 'api-keys',
    title: 'API Key 管理',
    sidebarLabel: 'API Key 管理',
    group: '用户接口',
    description: '创建、查看、删除 API Key 的接口说明'
  },
  {
    slug: 'collaboration',
    title: '协作成员令牌',
    sidebarLabel: '协作令牌',
    group: '协作接口',
    description: '获取与刷新协作成员令牌的接口'
  }
]

// Included endpoint families
export const INCLUDED_ENDPOINT_FAMILIES = [
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
  'POST /api/users/logout-all — 全部设备登出',
  'GET /api/users/me — 当前用户信息',
  'GET /api/users/{user_id} — 获取用户',
  'PUT /api/users/{user_id} — 更新用户',
  'DELETE /api/users/{user_id} — 删除用户',
  'DELETE /api/users/sessions/{session_id} — 撤销会话',
  'GET /api/users/me/totp — TOTP 状态',
  'POST /api/users/me/totp — 设置 TOTP',
  'POST /api/users/me/totp/verify — 验证 TOTP',
  'DELETE /api/users/me/totp — 禁用 TOTP',
  'GET /api/user/apikeys — 列出 API Key',
  'POST /api/user/apikeys — 创建 API Key',
  'DELETE /api/user/apikeys/{key_id} — 删除 API Key',
  'POST /api/user/apikeys/cleanup-expired — 清理过期 Key',
  'POST /api/rooms/member-token — 获取成员令牌',
  'POST /api/rooms/member-token/refresh — 刷新成员令牌',
  'GET /api/users — 用户列表（管理员）',
  'POST /api/users — 创建用户（管理员）',
  'POST /api/users/cleanup-sessions — 清理过期会话（管理员）'
]

// Explicit exclusions
export const EXCLUDED_ENDPOINT_FAMILIES = [
  '/api/internal/* — 内部接口',
  '/api/install/* — 安装引导接口',
  'GET /api/health — 健康检查',
  'GET /api/config — 配置信息',
  'POST /api/users/register — 用户注册',
  'POST /api/users/login — 用户登录',
  'POST /api/users/login-totp — TOTP 登录',
  'POST /api/users/refresh — 刷新 Token',
  'POST /api/users/logout — 单个登出',
  '/api/user/history/* — 用户 Paste 历史',
  'GET /api/users/{user_id}/sessions — 会话列表',
  'DELETE /api/users/{user_id}/sessions/others — 撤销其他会话',
  'POST /api/rooms — 创建房间',
  'GET /api/join/{pin_code} — 获取房间信息',
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
  dependsOn: string
  notes: string
}

export const API_KEY_CAPABILITY_MATRIX: ApiKeyMatrixEntry[] = [
  { endpoint: 'POST /api/users/logout-all', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'GET /api/users/me', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'GET /api/users/{user_id}', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'PUT /api/users/{user_id}', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'DELETE /api/users/{user_id}', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'DELETE /api/users/sessions/{session_id}', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'GET /api/users/me/totp', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'POST /api/users/me/totp', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'POST /api/users/me/totp/verify', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'DELETE /api/users/me/totp', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'GET /api/user/apikeys', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'POST /api/user/apikeys', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'DELETE /api/user/apikeys/{key_id}', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'POST /api/user/apikeys/cleanup-expired', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅支持 access_token' },
  { endpoint: 'GET /api/users', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅管理员可用，且仅支持 access_token' },
  { endpoint: 'POST /api/users', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅管理员可用，且仅支持 access_token' },
  { endpoint: 'POST /api/users/cleanup-sessions', capability: 'unsupported', dependsOn: 'get_current_user_by_access_token', notes: '仅管理员可用，且仅支持 access_token' },

  // Optional — depends(get_optional_user)
  { endpoint: 'POST /api/rooms/member-token', capability: 'optional', dependsOn: 'get_optional_user', notes: '可不登录获取，登录后使用真实用户名' },
  { endpoint: 'POST /api/rooms/member-token/refresh', capability: 'optional', dependsOn: 'get_optional_user', notes: '刷新成员令牌，可选携带身份' },

  // Unsupported — depends(get_current_user_and_session)
  { endpoint: 'GET /api/users/{user_id}/sessions', capability: 'unsupported', dependsOn: 'get_current_user_and_session', notes: '需要 session，不支持 API Key' },
  { endpoint: 'DELETE /api/users/{user_id}/sessions/others', capability: 'unsupported', dependsOn: 'get_current_user_and_session', notes: '需要 session，不支持 API Key' },

  // Unsupported — depends(get_current_user_with_key)
  { endpoint: 'GET /api/user/history', capability: 'unsupported', dependsOn: 'get_current_user_with_key', notes: '需要恢复用户密钥，不支持 API Key' },
  { endpoint: 'POST /api/user/history/import_guest', capability: 'unsupported', dependsOn: 'get_current_user_with_key', notes: '需要恢复用户密钥，不支持 API Key' },
  { endpoint: 'POST /api/user/history/{paste_id}', capability: 'unsupported', dependsOn: 'get_current_user_with_key', notes: '需要恢复用户密钥，不支持 API Key' },
  { endpoint: 'GET /api/user/history/{paste_id}', capability: 'unsupported', dependsOn: 'get_current_user_with_key', notes: '需要恢复用户密钥，不支持 API Key' },
  { endpoint: 'PUT /api/user/history/{paste_id}/star', capability: 'unsupported', dependsOn: 'get_current_user_with_key', notes: '需要恢复用户密钥，不支持 API Key' },
  { endpoint: 'DELETE /api/user/history/{paste_id}', capability: 'unsupported', dependsOn: 'get_current_user_with_key', notes: '需要恢复用户密钥，不支持 API Key' },

  // Unsupported — other auth models
  { endpoint: 'POST /api/users/register', capability: 'unsupported', dependsOn: '无认证', notes: '公开注册，不走 API Key' },
  { endpoint: 'POST /api/users/login', capability: 'unsupported', dependsOn: '无认证', notes: '登录接口，不走 API Key' },
  { endpoint: 'POST /api/users/login-totp', capability: 'unsupported', dependsOn: '无认证', notes: 'TOTP 登录，不走 API Key' },
  { endpoint: 'POST /api/users/refresh', capability: 'unsupported', dependsOn: 'Cookie refresh token', notes: '刷新 token 接口，不走 API Key' },
  { endpoint: 'POST /api/users/logout', capability: 'unsupported', dependsOn: 'Cookie refresh token', notes: '登出接口，不走 API Key' },
  { endpoint: '/api/pastes/* (写接口)', capability: 'unsupported', dependsOn: 'admin_key', notes: '依赖 admin_key，不走用户 API Key' },
  { endpoint: '/api/pastes/* (读接口)', capability: 'unsupported', dependsOn: '公开 / access_key / encryption_key / admin_key', notes: '按访问密钥验证，不走用户 API Key' },
  { endpoint: 'POST /api/rooms', capability: 'unsupported', dependsOn: 'member_token', notes: '依赖 member_token' },
  { endpoint: 'GET /api/join/{pin_code}', capability: 'unsupported', dependsOn: '无认证', notes: '公开接口' },
  { endpoint: 'POST /api/rooms/{room_id}/join', capability: 'unsupported', dependsOn: 'member_token', notes: '依赖 member_token' },
  { endpoint: 'GET /api/rooms/{room_id}/members', capability: 'unsupported', dependsOn: 'member_token', notes: '依赖 member_token' },
  { endpoint: 'POST /api/rooms/{room_id}/pastes', capability: 'unsupported', dependsOn: 'member_token', notes: '依赖 member_token' },
  { endpoint: 'GET /api/rooms/{room_id}/pastes', capability: 'unsupported', dependsOn: 'member_token', notes: '依赖 member_token' },
  { endpoint: 'DELETE /api/rooms/{room_id}/leave', capability: 'unsupported', dependsOn: 'member_token', notes: '依赖 member_token' },
  { endpoint: 'WS /api/rooms/{room_id}/ws', capability: 'unsupported', dependsOn: 'member_token', notes: 'WebSocket 连接，依赖 member_token' }
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
