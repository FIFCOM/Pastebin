import { ref } from 'vue'
import { setTheme } from 'mdui/functions/setTheme.js'
import Cookies from 'js-cookie'

type ThemeMode = 'auto' | 'light' | 'dark'
type ActualTheme = 'light' | 'dark'

// 全局状态（在模块作用域）
const themeMode = ref<ThemeMode>('auto')
const actualTheme = ref<ActualTheme>('light')

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
const applyTheme = (theme: ActualTheme) => {
  actualTheme.value = theme
  setTheme(theme)
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
  // 1. 读取用户设置
  const savedMode = Cookies.get('theme') as ThemeMode | undefined
  themeMode.value = savedMode || 'auto'
  
  // 2. 根据模式决定实际主题
  if (themeMode.value === 'auto') {
    actualTheme.value = getSystemTheme()
    
    // 监听系统主题变化
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQueryListener = handleSystemThemeChange
    mediaQuery.addEventListener('change', mediaQueryListener)
  } else {
    actualTheme.value = themeMode.value
  }
  
  // 3. 应用主题
  setTheme(actualTheme.value)
}

/**
 * 切换主题模式
 */
const toggleTheme = () => {
  // 移除旧的监听器
  if (mediaQuery && mediaQueryListener) {
    mediaQuery.removeEventListener('change', mediaQueryListener)
    mediaQueryListener = null
  }
  
  // 循环切换：auto -> light -> dark -> auto
  if (themeMode.value === 'auto') {
    themeMode.value = 'light'
    actualTheme.value = 'light'
    Cookies.set('theme', 'light', { expires: 30 })
  } else if (themeMode.value === 'light') {
    themeMode.value = 'dark'
    actualTheme.value = 'dark'
    Cookies.set('theme', 'dark', { expires: 30 })
  } else {
    // 切换回 auto，清除 cookie
    themeMode.value = 'auto'
    Cookies.remove('theme')
    
    // 重新读取系统主题并监听
    actualTheme.value = getSystemTheme()
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQueryListener = handleSystemThemeChange
    mediaQuery.addEventListener('change', mediaQueryListener)
  }
  
  applyTheme(actualTheme.value)
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
    toggleTheme,
    initTheme,
    cleanupTheme
  }
}