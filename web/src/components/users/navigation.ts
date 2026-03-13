export const USER_TAB_VALUES = ['profile', 'sessions', 'totp', 'apikeys', 'users'] as const

export type UserTabValue = (typeof USER_TAB_VALUES)[number]

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
  users: {
    value: 'users',
    label: '用户列表',
    group: '管理',
    icon: 'groups'
  }
}

export function isUserTabValue(value: unknown): value is UserTabValue {
  return typeof value === 'string' && (USER_TAB_VALUES as readonly string[]).includes(value)
}

export function normalizeUserTab(value: unknown, canAccessUsers: boolean): UserTabValue {
  if (!isUserTabValue(value)) return 'profile'
  if (value === 'users' && !canAccessUsers) return 'profile'
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
      items: [USER_NAVIGATION_ITEMS.users]
    })
  }

  return groups
}
