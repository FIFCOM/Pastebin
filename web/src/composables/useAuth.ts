import { ref, computed } from 'vue'
import type { UserResponse, LoginResponse } from '../services/auth'
import {
  registerUser,
  loginUser,
  loginUserWithTotp,
  fetchCurrentUser,
  logoutSession,
  logoutAllSessions
} from '../services/auth'
import { refreshAccessToken } from '../services/http'
import { AUTH_TOKEN_EVENT, clearAccessToken, loadAccessToken, saveAccessToken } from '../services/token'
import { useHistory, clearUserHistoryCache, resetHistoryState } from './useHistory'

/**
 * 全局认证状态（单例）
 */
const currentUser = ref<UserResponse | null>(null)
const accessToken = ref<string | null>(null)
const isAuthLoading = ref(false)
const isAuthInitialized = ref(false)

const isLoggedIn = computed(() => currentUser.value !== null)

let tokenListenerBound = false

function bindTokenListener(): void {
  if (tokenListenerBound) return
  tokenListenerBound = true

  window.addEventListener(AUTH_TOKEN_EVENT, (evt: Event) => {
    const token = (evt as CustomEvent).detail?.token as string | null | undefined
    accessToken.value = token ?? null
    if (!accessToken.value) {
      currentUser.value = null
    }
  })
}

/**
 * 初始化认证状态：
 * - access token 仅保存在内存中（避免 localStorage XSS 风险）
 * - 通过 refresh token HttpOnly Cookie 静默续期恢复会话
 */
async function initAuth(): Promise<void> {
  if (isAuthInitialized.value) {
    return
  }

  bindTokenListener()
  isAuthLoading.value = true
  try {
    const token = loadAccessToken()
    accessToken.value = token

    // 1) 先尝试使用内存中的 access token
    if (token) {
      try {
        currentUser.value = await fetchCurrentUser()
        return
      } catch {
        // ignore: fallback to refresh cookie
      }
    }

    // 2) 尝试使用 refresh token cookie 静默恢复会话（内存 access token 模式）
    try {
      const newToken = await refreshAccessToken()
      accessToken.value = newToken
      currentUser.value = await fetchCurrentUser()
    } catch {
      clearAccessToken()
      accessToken.value = null
      currentUser.value = null
    }
  } finally {
    isAuthInitialized.value = true
    isAuthLoading.value = false
  }
}

/**
 * 使用邮箱 + 密码登录
 */
async function login(email: string, password: string): Promise<LoginResponse> {
  isAuthLoading.value = true
  try {
    const resp = await loginUser(email, password)
    accessToken.value = resp.access_token
    currentUser.value = resp.user
    saveAccessToken(resp.access_token)
    resetHistoryState()
    // 登录成功后导入游客历史
    void useHistory().importGuestAndSync(resp.user.id)
    return resp
  } catch (e) {
    // 登录失败时清理本地状态，但把错误抛给调用方处理
    clearAccessToken()
    accessToken.value = null
    currentUser.value = null
    throw e
  } finally {
    isAuthLoading.value = false
  }
}

/**
 * 使用邮箱 + 密码 + TOTP 验证码登录
 */
async function loginWithTotp(
  email: string,
  password: string,
  totpCode: string
): Promise<LoginResponse> {
  isAuthLoading.value = true
  try {
    const resp = await loginUserWithTotp(email, password, totpCode)
    accessToken.value = resp.access_token
    currentUser.value = resp.user
    saveAccessToken(resp.access_token)
    resetHistoryState()
    void useHistory().importGuestAndSync(resp.user.id)
    return resp
  } catch (e) {
    clearAccessToken()
    accessToken.value = null
    currentUser.value = null
    throw e
  } finally {
    isAuthLoading.value = false
  }
}

/**
 * 注册后自动登录
 * - 先调用 /users/register
 * - 后使用注册时的 email + 原始密码调用 /users/login
 */
async function registerAndAutoLogin(
  email: string,
  password: string
): Promise<LoginResponse> {
  isAuthLoading.value = true
  try {
    await registerUser(email, password)
    const resp = await loginUser(email, password)
    accessToken.value = resp.access_token
    currentUser.value = resp.user
    saveAccessToken(resp.access_token)
    resetHistoryState()
    void useHistory().importGuestAndSync(resp.user.id)
    return resp
  } catch (e) {
    clearAccessToken()
    accessToken.value = null
    currentUser.value = null
    throw e
  } finally {
    isAuthLoading.value = false
  }
}

/**
 * 退出登录：清理本地 token 和用户信息
 */
function logout(): void {
  // 登出前清理当前用户的本地历史缓存
  if (currentUser.value) {
    clearUserHistoryCache(currentUser.value.id)
  }
  resetHistoryState()
  currentUser.value = null
  accessToken.value = null
  clearAccessToken()
  void logoutSession()
}

function logoutAll(): void {
  if (currentUser.value) {
    clearUserHistoryCache(currentUser.value.id)
  }
  resetHistoryState()
  currentUser.value = null
  accessToken.value = null
  clearAccessToken()
  void logoutAllSessions()
}

/**
 * 认证管理 composable
 */
export function useAuth() {
  return {
    // state
    currentUser,
    accessToken,
    isAuthLoading,
    isAuthInitialized,
    isLoggedIn,
    // actions
    initAuth,
    login,
    loginWithTotp,
    registerAndAutoLogin,
    logout,
    logoutAll
  }
}
