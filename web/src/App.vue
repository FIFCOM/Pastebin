<template>
  <div class="app-shell">
    <mdui-layout :class="['app-layout', { 'app-layout--sidebar-route': isAppSidebarRoute }]" full-height>
      <GlobalHeader v-if="!isInstallRoute"></GlobalHeader>
      <AppSidebar v-if="!isInstallRoute && isAppSidebarRoute"></AppSidebar>
      <mdui-layout-main ref="appMainRef" class="app-main">
        <div class="app-main-shell">
          <router-view />
        </div>
      </mdui-layout-main>
    </mdui-layout>
    <CollabJoinDialog v-if="!isInstallRoute"></CollabJoinDialog>
    <GlobalFooter v-if="!isInstallRoute"></GlobalFooter>
  </div>
</template>

<script setup lang="ts">
import 'mdui/mdui.css'
import 'mdui'

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import CollabJoinDialog from './components/collab/CollabJoinDialog.vue'
import GlobalHeader from './components/GlobalHeader.vue'
import GlobalFooter from './components/GlobalFooter.vue'
import { useAppSidebarState } from './composables/useAppSidebarState'
import { isDocsPath } from './content/api-docs'

const route = useRoute()
const { isAppSidebarOpen, setAppSidebarOpen, closeAppSidebar } = useAppSidebarState()
const isInstallRoute = computed(() => route.path === '/install' || route.path.startsWith('/install/'))
const isAppSidebarRoute = computed(() => isSidebarPath(route.path))
const appMainRef = ref<HTMLElement | null>(null)

let usersSidebarMediaQuery: MediaQueryList | null = null
let isDocumentScrollLocked = false
let lockedScrollY = 0

const initialDocumentStyles = {
  htmlOverflow: '',
  bodyOverflow: '',
  bodyPosition: '',
  bodyTop: '',
  bodyLeft: '',
  bodyRight: '',
  bodyWidth: ''
}

function shouldOpenUsersSidebarByDefault(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(min-width: 960px)').matches
}

function isSidebarPath(path: string): boolean {
  return path === '/users' || isDocsPath(path)
}

function resetAppMainHorizontalPadding(): void {
  const appMain = appMainRef.value
  if (!appMain) return

  appMain.style.paddingLeft = ''
  appMain.style.paddingRight = ''
}

function scheduleAppMainHorizontalPaddingReset(): void {
  void nextTick(() => {
    if (!isSidebarPath(route.path)) {
      resetAppMainHorizontalPadding()
    }
  })
}

function syncAppSidebarForRoute(path: string): void {
  if (path === '/install' || path.startsWith('/install/')) {
    closeAppSidebar()
    scheduleAppMainHorizontalPaddingReset()
    return
  }

  if (isSidebarPath(path)) {
    setAppSidebarOpen(shouldOpenUsersSidebarByDefault())
    return
  }

  closeAppSidebar()
  scheduleAppMainHorizontalPaddingReset()
}

function handleUsersSidebarBreakpointChange(event: MediaQueryListEvent): void {
  if (isSidebarPath(route.path)) {
    setAppSidebarOpen(event.matches)
  }

  syncDocumentScrollLock()
}

function shouldLockDocumentScroll(): boolean {
  if (typeof window === 'undefined') return false

  return !isInstallRoute.value
    && isAppSidebarOpen.value
    && window.matchMedia('(max-width: 959px)').matches
}

function lockDocumentScroll(): void {
  if (typeof window === 'undefined' || isDocumentScrollLocked) {
    return
  }

  const { documentElement, body } = document

  initialDocumentStyles.htmlOverflow = documentElement.style.overflow
  initialDocumentStyles.bodyOverflow = body.style.overflow
  initialDocumentStyles.bodyPosition = body.style.position
  initialDocumentStyles.bodyTop = body.style.top
  initialDocumentStyles.bodyLeft = body.style.left
  initialDocumentStyles.bodyRight = body.style.right
  initialDocumentStyles.bodyWidth = body.style.width

  lockedScrollY = window.scrollY
  documentElement.style.overflow = 'hidden'
  body.style.overflow = 'hidden'
  body.style.position = 'fixed'
  body.style.top = `-${lockedScrollY}px`
  body.style.left = '0'
  body.style.right = '0'
  body.style.width = '100%'
  isDocumentScrollLocked = true
}

function unlockDocumentScroll(): void {
  if (typeof window === 'undefined' || !isDocumentScrollLocked) {
    return
  }

  const { documentElement, body } = document

  documentElement.style.overflow = initialDocumentStyles.htmlOverflow
  body.style.overflow = initialDocumentStyles.bodyOverflow
  body.style.position = initialDocumentStyles.bodyPosition
  body.style.top = initialDocumentStyles.bodyTop
  body.style.left = initialDocumentStyles.bodyLeft
  body.style.right = initialDocumentStyles.bodyRight
  body.style.width = initialDocumentStyles.bodyWidth

  window.scrollTo(0, lockedScrollY)
  lockedScrollY = 0
  isDocumentScrollLocked = false
}

function syncDocumentScrollLock(): void {
  if (shouldLockDocumentScroll()) {
    lockDocumentScroll()
    return
  }

  unlockDocumentScroll()
}

watch(
  () => route.path,
  (path) => {
    syncAppSidebarForRoute(path)
    syncDocumentScrollLock()
  },
  { immediate: true }
)

watch(isAppSidebarOpen, () => {
  syncDocumentScrollLock()
})

onMounted(() => {
  if (typeof window !== 'undefined') {
    usersSidebarMediaQuery = window.matchMedia('(min-width: 960px)')
    usersSidebarMediaQuery.addEventListener('change', handleUsersSidebarBreakpointChange)
    syncAppSidebarForRoute(route.path)
    syncDocumentScrollLock()
  }
})

onBeforeUnmount(() => {
  usersSidebarMediaQuery?.removeEventListener('change', handleUsersSidebarBreakpointChange)
  usersSidebarMediaQuery = null
  unlockDocumentScroll()
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-layout {
  flex: 1 1 auto;
  min-height: 0;
}

.app-main {
  width: 100%;
  min-height: 0;
}

.app-layout:not(.app-layout--sidebar-route) .app-main {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.app-main-shell {
  box-sizing: border-box;
  width: 96%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 8px;
}

@media (min-width: 600px) {
  .app-main-shell {
    width: 94%;
  }
}

@media (min-width: 1024px) {
  .app-main-shell {
    width: 92%;
  }
}

/* 主题动画过渡 */
:deep(html), :deep(body) {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}

/* MDUI主题类样式 - 让MDUI自己管理颜色 */

/* 布局容器动画 */
:deep(.mdui-layout) {
  background-color: var(--bg-color);
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1);
}

:deep(.mdui-layout-main) {
  background-color: var(--bg-color);
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1);
  scrollbar-gutter: stable;
}

/* 卡片和表面动画 */
:deep(.mdui-card) {
  background-color: var(--surface-color);
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1);
}

/* 按钮动画 */
:deep(.mdui-button) {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}

/* 确保背景动画覆盖整个页面 */
:deep(html) {
  height: 100%;
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1);
}

:deep(body) {
  min-height: 100vh;
  margin: 0;
  padding: 0;
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1);
  scrollbar-gutter: stable;
}

/* 确保MDUI组件的动画效果 */
:deep(.mdui-theme-transition) {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1),
              border-color 150ms cubic-bezier(0.2, 0, 0, 1);
}

/* 输入框和表单元素动画 */
:deep(.mdui-text-field) {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}

:deep(.mdui-text-field:focus) {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1),
              border-color 150ms cubic-bezier(0.2, 0, 0, 1);
}

/* 菜单和下拉框动画 */
:deep(.mdui-menu) {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1);
}

:deep(.mdui-menu-item) {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}

/* 对话框和模态框动画 */
:deep(.mdui-dialog) {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1);
}
</style>
