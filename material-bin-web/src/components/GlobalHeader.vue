<template>
  <mdui-top-app-bar>
    <mdui-top-app-bar-title> # Material Bin </mdui-top-app-bar-title>
    <div class="header-spacer"></div>

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
          <span class="user-initial">
            {{ userInitial }}
          </span>
        </mdui-button-icon>
        <mdui-menu>
          <mdui-menu-item disabled>
            已登录为：{{ currentUser?.username }}
          </mdui-menu-item>
          <mdui-menu-item @click="handleLogout">
            退出登录
          </mdui-menu-item>
        </mdui-menu>
      </mdui-dropdown>
    </template>

    <!-- 主题切换按钮 -->
    <mdui-button-icon
      id="themeIcon"
      @click="handleToggleTheme()"
      class="theme-toggle-btn"
      :data-theme-mode="themeMode"
    >
      <mdui-icon-brightness-auto class="theme-icon auto-icon" />
      <mdui-icon-light-mode class="theme-icon light-icon" />
      <mdui-icon-dark-mode class="theme-icon dark-icon" />
    </mdui-button-icon>
  </mdui-top-app-bar>
</template>

<script setup lang="ts">
import '@mdui/icons/brightness-auto.js'
import '@mdui/icons/light-mode.js'
import '@mdui/icons/dark-mode.js'

import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/dropdown.js'
import 'mdui/components/menu.js'
import 'mdui/components/menu-item.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'

import { useTheme } from '../composables/useTheme'
import { useAuth } from '../composables/useAuth'

const { themeMode, toggleTheme, initTheme, cleanupTheme } = useTheme()
const { isLoggedIn, currentUser, logout } = useAuth()

const router = useRouter()
const route = useRoute()

const userInitial = computed(() => {
  const name = currentUser.value?.username || ''
  return name ? name.charAt(0).toUpperCase() : 'U'
})

const handleToggleTheme = () => {
  toggleTheme()
  changeThemeIcon()
}

const changeThemeIcon = () => {
  // 图标切换动画通过CSS类控制
  const themeIcon = document.getElementById('themeIcon')
  if (themeIcon) {
    // 添加过渡动画类
    themeIcon.classList.add('theme-icon-transition')
    setTimeout(() => {
      themeIcon.classList.remove('theme-icon-transition')
    }, 150)
  }
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

onMounted(() => {
  initTheme()
  changeThemeIcon()
})

onUnmounted(() => {
  cleanupTheme()
})
</script>

<style scoped>
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
}

.user-initial {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: var(--mdui-color-primary-container);
  color: var(--mdui-color-on-primary-container);
  font-size: 14px;
  font-weight: 600;
}

/* 主题切换按钮样式 */
.theme-toggle-btn {
  position: relative;
  transition: transform 150ms cubic-bezier(0.2, 0, 0, 1);
}

.theme-toggle-btn:hover {
  transform: scale(1.1);
}

.theme-toggle-btn:active {
  transform: scale(0.95);
}

/* 主题图标动画 */
.theme-icon {
  position: absolute;
  transition: opacity 150ms cubic-bezier(0.2, 0, 0, 1),
              transform 150ms cubic-bezier(0.2, 0, 0, 1);
  font-size: 24px;
}

/* 默认隐藏所有图标 */
.light-icon,
.dark-icon,
.auto-icon {
  opacity: 0;
  transform: rotate(-180deg) scale(0.8); /* 点击时旋转，初始缩小 */
}

/* auto 模式：显示 auto 图标 */
.theme-toggle-btn[data-theme-mode="auto"] .auto-icon {
  opacity: 1;
  transform: rotate(0deg) scale(1);
}

/* light 模式：显示 light 图标 */
.theme-toggle-btn[data-theme-mode="light"] .light-icon {
  opacity: 1;
  transform: rotate(0deg) scale(1);
}

/* dark 模式：显示 dark 图标 */
.theme-toggle-btn[data-theme-mode="dark"] .dark-icon {
  opacity: 1;
  transform: rotate(0deg) scale(1);
}

/* 图标过渡动画类 */
.theme-icon-transition .theme-icon {
  transition: opacity 150ms cubic-bezier(0.2, 0, 0, 1),
              transform 150ms cubic-bezier(0.2, 0, 0, 1);
}
</style>

<style>
/* Top App Bar动画 */
mdui-top-app-bar {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}
</style>
