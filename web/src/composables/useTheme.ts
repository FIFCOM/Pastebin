import { ref } from 'vue'
import { setTheme } from 'mdui/functions/setTheme.js'
import { setColorScheme } from 'mdui/functions/setColorScheme.js'

type ThemeMode = 'auto' | 'light' | 'dark'
type ActualTheme = 'light' | 'dark'

// 预设主题色列表，供全局复用
export const presetColors = [
  '#0061a4',
  '#ffce22',
  '#006874',
  '#006e1c',
  '#9f86ff'
] as const

type ThemeColor = (typeof presetColors)[number] | string

const themeMode = ref<ThemeMode>('auto')
const actualTheme = ref<ActualTheme>('light')
const themeColor = ref<ThemeColor>(presetColors[0])

let mediaQuery: MediaQueryList | null = null
let mediaQueryListener: ((e: MediaQueryListEvent) => void) | null = null

const isThemeMode = (value: string | null): value is ThemeMode => {
  return value === 'auto' || value === 'light' || value === 'dark'
}

const isValidHexColor = (value: unknown): value is string => {
  return typeof value === 'string' && /^#[0-9a-fA-F]{6}$/.test(value)
}

const syncThemeMode = (mode: ActualTheme) => {
  setTheme(mode)
}

const syncThemeColor = (color: string) => {
  setColorScheme(color)
}

/**
 * 获取系统主题偏好
 */
const getSystemTheme = (): ActualTheme => {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)')
  return prefersDark.matches ? 'dark' : 'light'
}

/**
 * 应用主题
 */
const applyTheme = (newTheme: ThemeMode) => {
  // 切换前统一使用 cleanupTheme 清理旧的系统主题监听
  cleanupTheme()

  themeMode.value = newTheme

  // 判断 newTheme 是否为 auto
  if (newTheme === 'auto') {
    // 跟随系统：读取当前系统主题并绑定监听
    actualTheme.value = getSystemTheme()

    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQueryListener = handleSystemThemeChange
    mediaQuery.addEventListener('change', mediaQueryListener)
  } else {
    // 固定为 light / dark：不绑定系统监听
    actualTheme.value = newTheme
  }

  localStorage.setItem('theme', newTheme)
  syncThemeMode(actualTheme.value)
}

const applyColor = (newColor: ThemeColor) => {
  // 简单格式校验：必须为 #RRGGBB，否则回退为当前已记录或默认颜色
  const fallbackColor = isValidHexColor(themeColor.value) ? themeColor.value : presetColors[0]
  const finalColor = isValidHexColor(newColor) ? newColor : fallbackColor

  themeColor.value = finalColor
  localStorage.setItem('theme_color', finalColor)
  syncThemeColor(finalColor)
}

/**
 * 系统主题变化处理
 */
const handleSystemThemeChange = (e: MediaQueryListEvent) => {
  if (themeMode.value !== 'auto') {
    return
  }
  actualTheme.value = e.matches ? 'dark' : 'light'
  syncThemeMode(actualTheme.value)
}

/**
 * 初始化主题
 */
const initTheme = () => {
  // 读取用户设置（默认 auto）
  const rawMode = localStorage.getItem('theme')
  const savedMode = isThemeMode(rawMode) ? rawMode : 'auto'

  // 通过 applyTheme 统一处理 themeMode、actualTheme 和监听器
  applyTheme(savedMode)

  // 读取并应用保存的颜色（通过 applyColor 统一处理和校验）
  const savedColor = localStorage.getItem('theme_color') as ThemeColor | null
  if (savedColor) {
    applyColor(savedColor)
  } else {
    applyColor(themeColor.value)
  }
}

/**
 * 切换主题模式（循环：auto -> light -> dark -> auto）
 */
const toggleTheme = () => {
  let nextTheme: ThemeMode
  if (themeMode.value === 'auto') {
    nextTheme = 'light'
  } else if (themeMode.value === 'light') {
    nextTheme = 'dark'
  } else {
    nextTheme = 'auto'
  }

  // 所有监听处理统一交给 applyTheme
  applyTheme(nextTheme)
}

/**
 * 设置为指定主题模式
 */
const setThemeMode = (mode: ThemeMode) => {
  if (themeMode.value === mode) {
    return
  }
  applyTheme(mode)
}

/**
 * 清理监听器
 */
const cleanupTheme = () => {
  if (mediaQuery && mediaQueryListener) {
    mediaQuery.removeEventListener('change', mediaQueryListener)
    mediaQueryListener = null
    mediaQuery = null
  }
}

/**
 * 主题管理 Composable
 */
export const useTheme = () => {
  return {
    themeMode,
    actualTheme,
    themeColor,
    toggleTheme,
    setThemeMode,
    initTheme,
    cleanupTheme,
    applyColor
  }
}
