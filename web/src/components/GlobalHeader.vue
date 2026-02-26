<template>
  <mdui-top-app-bar>
    <mdui-top-app-bar-title> # Material Bin </mdui-top-app-bar-title>
    <div class="header-spacer"></div>

    <!-- 功能图标按钮 -->
    <mdui-button-icon>
      <mdui-icon-groups />
    </mdui-button-icon>
    <mdui-button-icon @click="goHistory">
      <mdui-icon-history />
    </mdui-button-icon>
    <mdui-button-icon>
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
import '@mdui/icons/account-circle.js'
import '@mdui/icons/groups.js'
import '@mdui/icons/history.js'
import '@mdui/icons/share.js'

import { useRoute, useRouter } from 'vue-router'
import { snackbar } from 'mdui/functions/snackbar.js'
import 'mdui/components/dropdown.js'
import 'mdui/components/menu.js'
import 'mdui/components/menu-item.js'
import 'mdui/components/button.js'
import 'mdui/components/button-icon.js'

import { useAuth } from '../composables/useAuth'
const { isLoggedIn, currentUser, logout } = useAuth()

const router = useRouter()
const route = useRoute()

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
  --mdui-icon-size: 22px;
}

</style>

<style>
/* Top App Bar动画 */
mdui-top-app-bar {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}
</style>
