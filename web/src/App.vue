<template>
  <div class="app-shell">
    <mdui-layout class="app-layout" full-height>
      <GlobalHeader v-if="!isInstallRoute"></GlobalHeader>
      <AppSidebar v-if="!isInstallRoute"></AppSidebar>
      <mdui-layout-main class="app-main">
        <div class="app-main-shell">
          <router-view />
        </div>
      </mdui-layout-main>
    </mdui-layout>
    <GlobalFooter v-if="!isInstallRoute"></GlobalFooter>
  </div>
</template>

<script setup lang="ts">
import 'mdui/mdui.css'
import 'mdui'

import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import GlobalHeader from './components/GlobalHeader.vue'
import GlobalFooter from './components/GlobalFooter.vue'
import { useAppSidebarState } from './composables/useAppSidebarState'
import { useAuth } from './composables/useAuth'

const route = useRoute()
const { initAuth } = useAuth()
const { setAppSidebarOpen, closeAppSidebar } = useAppSidebarState()
const isInstallRoute = computed(() => route.path === '/install' || route.path.startsWith('/install/'))

let usersSidebarMediaQuery: MediaQueryList | null = null

function shouldOpenUsersSidebarByDefault(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(min-width: 960px)').matches
}

function syncAppSidebarForRoute(path: string): void {
  if (path === '/install' || path.startsWith('/install/')) {
    closeAppSidebar()
    return
  }

  if (path === '/users') {
    setAppSidebarOpen(shouldOpenUsersSidebarByDefault())
    return
  }

  closeAppSidebar()
}

function handleUsersSidebarBreakpointChange(event: MediaQueryListEvent): void {
  if (route.path !== '/users') return
  setAppSidebarOpen(event.matches)
}

watch(
  () => route.path,
  (path) => {
    syncAppSidebarForRoute(path)
  },
  { immediate: true }
)

onMounted(() => {
  if (typeof window !== 'undefined') {
    usersSidebarMediaQuery = window.matchMedia('(min-width: 960px)')
    usersSidebarMediaQuery.addEventListener('change', handleUsersSidebarBreakpointChange)
    syncAppSidebarForRoute(route.path)
  }

  if (isInstallRoute.value) return
  initAuth().catch((e) => {
    console.error('Failed to initialize auth on app mount', e)
  })
})

onBeforeUnmount(() => {
  usersSidebarMediaQuery?.removeEventListener('change', handleUsersSidebarBreakpointChange)
  usersSidebarMediaQuery = null
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
