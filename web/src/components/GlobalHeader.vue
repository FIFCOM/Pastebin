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
        <button class="brand-link" type="button" @click="goHome">
          <span>Material Bin</span>
        </button>
      </div>
    </mdui-top-app-bar-title>
    <div class="header-spacer"></div>

    <template v-for="action in activeHeaderActions" :key="action.flashKey">
      <mdui-button-icon
        v-if="action.kind === 'icon'"
        class="header-action header-action-icon"
        :class="{
          'header-action--active': action.active,
          'header-action--flash': action.flashing
        }"
        :title="action.label"
        :aria-label="action.ariaLabel"
        :aria-pressed="action.active ? 'true' : undefined"
        :disabled="action.disabled"
        @click="handleActionClick(action)"
      >
        <mdui-icon v-if="action.icon" :name="action.icon"></mdui-icon>
        <span v-else class="header-action-fallback">{{ action.label }}</span>
      </mdui-button-icon>

      <mdui-button
        v-else
        class="header-action header-action-text"
        :class="{
          'header-action--active': action.active,
          'header-action--flash': action.flashing
        }"
        variant="text"
        :title="action.label"
        :aria-label="action.ariaLabel"
        :aria-pressed="action.active ? 'true' : undefined"
        :disabled="action.disabled"
        @click="handleActionClick(action)"
      >
        <mdui-icon v-if="action.icon" slot="icon" :name="action.icon"></mdui-icon>
        {{ action.label }}
      </mdui-button>
    </template>

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

import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/dropdown.js'
import 'mdui/components/menu.js'
import 'mdui/components/menu-item.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'
import 'mdui/components/icon.js'

import { useAuth } from '../composables/useAuth'
import { useAppSidebarState } from '../composables/useAppSidebarState'
import { activeHeaderActions, type ActiveHeaderAction } from '../composables/useHeaderActions'

const { isLoggedIn, currentUser, logout } = useAuth()
const { toggleAppSidebar } = useAppSidebarState()

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

const handleMenuClick = () => {
  toggleAppSidebar()
}

const goHome = () => {
  router.push('/')
}

function handleActionClick(action: ActiveHeaderAction): void {
  if (action.disabled || !action.onClick) return
  void Promise.resolve(action.onClick()).catch(() => {
    snackbar({ message: '操作失败，请稍后重试', closeable: true })
  })
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

.header-action {
  flex-shrink: 0;
}

.header-action-icon {
  border-radius: 999px;
}

.header-action-text {
  margin-inline: 2px;
}

.header-action-fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  font-size: 0.78rem;
  font-weight: 700;
}

.header-action--active {
  color: rgb(var(--mdui-color-primary));
}

.header-action--active::part(container) {
  background: rgb(var(--mdui-color-primary-container));
  color: rgb(var(--mdui-color-on-primary-container));
}

.header-action--flash,
.header-action--flash::part(container) {
  animation: headerActionPulse 720ms cubic-bezier(0.2, 0, 0, 1) 3;
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

@keyframes headerActionPulse {
  0%,
  100% {
    background-color: transparent;
    box-shadow: 0 0 0 0 rgb(var(--mdui-color-primary) / 0);
  }

  45% {
    background-color: rgb(var(--mdui-color-primary-container));
    box-shadow: 0 0 0 8px rgb(var(--mdui-color-primary) / 0.12);
    color: rgb(var(--mdui-color-on-primary-container));
  }
}

@keyframes headerActionReducedEmphasis {
  0%,
  100% {
    background-color: transparent;
  }

  50% {
    background-color: rgb(var(--mdui-color-primary-container));
  }
}

@media (prefers-reduced-motion: reduce) {
  .header-action--flash,
  .header-action--flash::part(container) {
    animation: headerActionReducedEmphasis 220ms ease-out 1 both;
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
