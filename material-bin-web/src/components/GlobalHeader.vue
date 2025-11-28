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

  </mdui-top-app-bar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
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

const userInitial = computed(() => {
  const name = currentUser.value?.username || ''
  return name ? name.charAt(0).toUpperCase() : 'U'
})

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

</style>

<style>
/* Top App Bar动画 */
mdui-top-app-bar {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}
</style>
