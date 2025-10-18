<template>
  <mdui-top-app-bar>
    <mdui-top-app-bar-title> # Material Bin </mdui-top-app-bar-title>
    <div style="flex-grow: 1"></div>
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

import { onMounted, onUnmounted } from 'vue'
import { useTheme } from '../composables/useTheme'

const { themeMode, toggleTheme, initTheme, cleanupTheme } = useTheme()

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

onMounted(() => {
  initTheme()
  changeThemeIcon()
})

onUnmounted(() => {
  cleanupTheme()
})
</script>

<style scoped>
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
  transform: scale(0.8);
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
