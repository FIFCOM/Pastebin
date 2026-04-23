<template>
  <mdui-top-app-bar ref="topAppBarRef">
    <mdui-top-app-bar-title>
      <div class="brand-group">
        <mdui-button-icon
          class="menu-button"
          aria-label="打开侧边栏"
          @click="handleMenuClick"
        >
          <mdui-icon-menu />
        </mdui-button-icon>
        <button class="brand-link" type="button" @click="goHome">Material Bin</button>
      </div>
    </mdui-top-app-bar-title>
    <div class="header-spacer"></div>

    <!-- 功能图标按钮 -->
    <mdui-button-icon aria-label="打开加入房间界面" @click="handleOpenJoinDialog">
      <mdui-icon-groups />
    </mdui-button-icon>
    <mdui-button-icon aria-label="查看历史记录" @click="goHistory">
      <mdui-icon-history />
    </mdui-button-icon>
    <mdui-button-icon aria-label="分享功能（暂未开放）">
      <mdui-icon-share />
    </mdui-button-icon>

    <!-- 未登录：显示登录按钮 -->
    <template v-if="!isLoggedIn">
      <mdui-button
        class="login-button"
        variant="text"
        @click="handleLoginClick"
      >
        登录
      </mdui-button>
    </template>

    <!-- 已登录：显示用户下拉菜单（使用 mdui-dropdown） -->
    <template v-else>
      <mdui-dropdown>
        <mdui-button-icon
          slot="trigger"
          class="user-button"
        >
          <mdui-icon-account-circle />
        </mdui-button-icon>
        <mdui-menu>
          <mdui-menu-item disabled>
            已登录为：{{ currentUser?.username }}
          </mdui-menu-item>
          <mdui-menu-item @click="goUserManagement">
            用户管理
          </mdui-menu-item>
          <mdui-menu-item @click="handleLogout">
            退出登录
          </mdui-menu-item>
        </mdui-menu>
      </mdui-dropdown>
    </template>

  </mdui-top-app-bar>
</template>

<script setup lang="ts">
import '@mdui/icons/menu.js'
import '@mdui/icons/account-circle.js'
import '@mdui/icons/groups.js'
import '@mdui/icons/history.js'
import '@mdui/icons/share.js'

import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/dropdown.js'
import 'mdui/components/menu.js'
import 'mdui/components/menu-item.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'

import { useAuth } from '../composables/useAuth'
import { useAppSidebarState } from '../composables/useAppSidebarState'
import { useCollabDialogState } from '../composables/useCollabDialogState'

const { isLoggedIn, currentUser, logout } = useAuth()
const { toggleAppSidebar } = useAppSidebarState()
const { openJoinDialog } = useCollabDialogState()

const router = useRouter()
const route = useRoute()
const topAppBarRef = ref<HTMLElement | null>(null)

let headerOffsetAnimationFrame = 0
let headerResizeObserver: ResizeObserver | null = null

function getVisibleHeaderHeight(): number {
  if (typeof window === 'undefined' || !topAppBarRef.value) {
    return 0
  }

  const rect = topAppBarRef.value.getBoundingClientRect()
  const visibleTop = Math.max(rect.top, 0)
  const visibleBottom = Math.min(rect.bottom, window.innerHeight)

  return Math.max(0, Math.min(rect.height, visibleBottom - visibleTop))
}

function syncHeaderOffset(): void {
  if (typeof document === 'undefined') {
    return
  }

  document.documentElement.style.setProperty('--app-header-offset', `${getVisibleHeaderHeight()}px`)
}

function scheduleHeaderOffsetSync(): void {
  if (typeof window === 'undefined' || headerOffsetAnimationFrame) {
    return
  }

  headerOffsetAnimationFrame = window.requestAnimationFrame(() => {
    headerOffsetAnimationFrame = 0
    syncHeaderOffset()
  })
}

const handleLoginClick = () => {
  // 已在登录页时不再重复跳转，避免 redirect 参数不断叠加
  if (route.name === 'Login') {
    return
  }

  let redirect = '/'

  // 如果当前在注册页，优先沿用已有的 redirect（如果有的话）
  if (route.name === 'Register') {
    redirect = (route.query.redirect as string | undefined) || '/'
  } else {
    // 其它页面使用当前完整路径作为 redirect
    redirect = route.fullPath || '/'
  }

  router.push({
    path: '/login',
    query: redirect !== '/' ? { redirect } : undefined
  })
}

const handleLogout = () => {
  logout()
  snackbar({ message: '已退出登录' })
  router.push('/')
}

const goUserManagement = () => {
  router.push('/users')
}

const goHistory = () => {
  router.push('/history')
}

const handleOpenJoinDialog = () => {
  openJoinDialog()
}

const handleMenuClick = () => {
  toggleAppSidebar()
}

const goHome = () => {
  router.push('/')
}

onMounted(() => {
  if (typeof window === 'undefined') {
    return
  }

  scheduleHeaderOffsetSync()
  document.addEventListener('scroll', scheduleHeaderOffsetSync, { capture: true, passive: true })
  window.addEventListener('resize', scheduleHeaderOffsetSync)

  if (topAppBarRef.value) {
    headerResizeObserver = new ResizeObserver(() => {
      scheduleHeaderOffsetSync()
    })
    headerResizeObserver.observe(topAppBarRef.value)
  }
})

onBeforeUnmount(() => {
  if (typeof window === 'undefined') {
    return
  }

  document.removeEventListener('scroll', scheduleHeaderOffsetSync, true)
  window.removeEventListener('resize', scheduleHeaderOffsetSync)

  if (headerOffsetAnimationFrame) {
    window.cancelAnimationFrame(headerOffsetAnimationFrame)
    headerOffsetAnimationFrame = 0
  }

  headerResizeObserver?.disconnect()
  headerResizeObserver = null
  document.documentElement.style.removeProperty('--app-header-offset')
})
</script>

<style scoped>
.brand-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.menu-button {
  flex-shrink: 0;
}

.brand-link {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
}

.brand-link:hover {
  color: rgb(var(--mdui-color-primary));
}

.brand-link:focus-visible {
  outline: 2px solid rgb(var(--mdui-color-primary));
  outline-offset: 4px;
  border-radius: 999px;
}

.header-spacer {
  flex-grow: 1;
}

/* 登录按钮 */
.login-button {
  margin-right: 8px;
}

/* 用户按钮 */
.user-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 4px;
  --mdui-icon-size: 22px;
}

@media (max-width: 640px) {
  .brand-link {
    font-size: 0.95rem;
  }
}

</style>

<style>
/* Top App Bar动画 */
mdui-top-app-bar {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}
</style>
