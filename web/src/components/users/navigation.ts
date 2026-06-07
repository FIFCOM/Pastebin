export const USER_TAB_VALUES = [
  'profile',
  'sessions',
  'totp',
  'apikeys',
  'admin-overview',
  'admin-users',
  'admin-pastes',
  'admin-cleanup'
] as const

export type UserTabValue = (typeof USER_TAB_VALUES)[number]
export type LegacyUserTabValue = 'users'

export type UserNavigationItem = {
  value: UserTabValue
  label: string
  group: string
  icon: string
}

export type UserNavigationGroup = {
  label: string
  icon: string
  items: UserNavigationItem[]
}

export const USER_NAVIGATION_ITEMS: Record<UserTabValue, UserNavigationItem> = {
  profile: {
    value: 'profile',
    label: '我的账户',
    group: '账户',
    icon: 'manage_accounts'
  },
  sessions: {
    value: 'sessions',
    label: '会话',
    group: '账户',
    icon: 'history'
  },
  totp: {
    value: 'totp',
    label: '两步验证',
    group: '安全',
    icon: 'verified_user'
  },
  apikeys: {
    value: 'apikeys',
    label: 'API Keys',
    group: '安全',
    icon: 'vpn_key'
  },
  'admin-overview': {
    value: 'admin-overview',
    label: '管理概览',
    group: '管理',
    icon: 'dashboard'
  },
  'admin-users': {
    value: 'admin-users',
    label: '用户列表',
    group: '管理',
    icon: 'groups'
  },
  'admin-pastes': {
    value: 'admin-pastes',
    label: 'Paste 管理',
    group: '管理',
    icon: 'content_paste'
  },
  'admin-cleanup': {
    value: 'admin-cleanup',
    label: '清理任务',
    group: '管理',
    icon: 'cleaning_services'
  }
}

export function isUserTabValue(value: unknown): value is UserTabValue {
  return typeof value === 'string' && (USER_TAB_VALUES as readonly string[]).includes(value)
}

export function isAdminTabValue(value: unknown): value is UserTabValue {
  return typeof value === 'string' && value.startsWith('admin-') && isUserTabValue(value)
}

export function normalizeUserTab(value: unknown, canAccessUsers: boolean): UserTabValue {
  if (value === 'users') return canAccessUsers ? 'admin-users' : 'profile'
  if (!isUserTabValue(value)) return 'profile'
  if (isAdminTabValue(value) && !canAccessUsers) return 'profile'
  return value
}

export function getUserNavigationGroups(canAccessUsers: boolean): UserNavigationGroup[] {
  const groups = [
    {
      label: '账户',
      icon: 'account_circle',
      items: [USER_NAVIGATION_ITEMS.profile, USER_NAVIGATION_ITEMS.sessions]
    },
    {
      label: '安全',
      icon: 'shield',
      items: [USER_NAVIGATION_ITEMS.totp, USER_NAVIGATION_ITEMS.apikeys]
    }
  ]

  if (canAccessUsers) {
    groups.push({
      label: '管理',
      icon: 'admin_panel_settings',
      items: [
        USER_NAVIGATION_ITEMS['admin-overview'],
        USER_NAVIGATION_ITEMS['admin-users'],
        USER_NAVIGATION_ITEMS['admin-pastes'],
        USER_NAVIGATION_ITEMS['admin-cleanup']
      ]
    })
  }

  return groups
}
