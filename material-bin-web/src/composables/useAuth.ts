import { ref, computed } from 'vue'
import type { UserResponse, LoginResponse } from '../services/auth'
import {
  registerUser,
  loginUser,
  fetchCurrentUser,
  saveToken,
  loadToken,
  clearToken
} from '../services/auth'

/**
 * 全局认证状态（单例）
 */
const currentUser = ref<UserResponse | null>(null)
const accessToken = ref<string | null>(null)
const isAuthLoading = ref(false)
const isAuthInitialized = ref(false)

const isLoggedIn = computed(() => currentUser.value !== null)

/**
 * 从 localStorage 读取 token 并尝试恢复当前用户
 */
async function initAuth(): Promise<void> {
  if (isAuthInitialized.value) {
    return
  }

  isAuthLoading.value = true
  try {
    const storedToken = loadToken()
    if (!storedToken) {
      isAuthInitialized.value = true
      return
    }

    try {
      const user = await fetchCurrentUser(storedToken)
      accessToken.value = storedToken
      currentUser.value = user
    } catch (e) {
      // token 无效或用户不存在，清理本地状态
      clearToken()
      accessToken.value = null
      currentUser.value = null
      throw e
    } finally {
      isAuthInitialized.value = true
    }
  } finally {
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
    saveToken(resp.access_token)
    return resp
  } catch (e) {
    // 登录失败时清理本地状态，但把错误抛给调用方处理
    clearToken()
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
    saveToken(resp.access_token)
    return resp
  } catch (e) {
    clearToken()
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
  clearToken()
  accessToken.value = null
  currentUser.value = null
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
    registerAndAutoLogin,
    logout
  }
}