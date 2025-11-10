import { ref } from 'vue'
import { setTheme } from 'mdui/functions/setTheme.js'
import { setColorScheme } from 'mdui/functions/setColorScheme.js';
import Cookies from 'js-cookie'

type ThemeMode = 'auto' | 'light' | 'dark'
type ActualTheme = 'light' | 'dark'
type ThemeColor = '#0061a4' | '#ffb300' | '#f4511e' | '#0b8043' | '#ab47bc' | string


const themeMode = ref<ThemeMode>('auto')
const actualTheme = ref<ActualTheme>('light')
const themeColor = ref<ThemeColor>('#0061a4')

let mediaQuery: MediaQueryList | null = null
let mediaQueryListener: ((e: MediaQueryListEvent) => void) | null = null

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

  Cookies.set('theme', newTheme, { expires: 30 })
  setTheme(actualTheme.value)
}

const applyColor = (newColor: ThemeColor) => {
  // 简单格式校验：必须为 #RRGGBB，否则回退为当前已记录或默认颜色
  const isValidHex =
    typeof newColor === 'string' &&
    /^#[0-9a-fA-F]{6}$/.test(newColor)

  const finalColor = isValidHex ? newColor : themeColor.value

  themeColor.value = finalColor
  Cookies.set('theme_color', finalColor, { expires: 30 })
  setColorScheme(finalColor)
}


/**
 * 系统主题变化处理
 */
const handleSystemThemeChange = (e: MediaQueryListEvent) => {
  if (themeMode.value === 'auto') {
    const newTheme = e.matches ? 'dark' : 'light'
    applyTheme(newTheme)
  }
}

/**
 * 初始化主题
 */
const initTheme = () => {
  // 读取用户设置（默认 auto）
  const savedMode = (Cookies.get('theme') as ThemeMode | undefined) || 'auto'

  // 通过 applyTheme 统一处理 themeMode、actualTheme 和监听器
  applyTheme(savedMode)

  // 读取并应用保存的颜色（通过 applyColor 统一处理和校验）
  const savedColor = Cookies.get('theme_color') as ThemeColor | undefined
  if (savedColor) {
    applyColor(savedColor)
  } else {
    applyColor(themeColor.value)
  }
}

/**
 * 切换主题模式
 */
const toggleTheme = () => {
  // 循环切换：auto -> light -> dark -> auto
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
    initTheme,
    cleanupTheme,
    applyColor
  }
}