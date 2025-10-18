<template>
  <mdui-top-app-bar>
    <mdui-top-app-bar-title> # Material Bin </mdui-top-app-bar-title>
    <div style="flex-grow: 1"></div>
    <mdui-button-icon id="themeIcon" @click="toggleTheme()" class="theme-toggle-btn">
      <mdui-icon-light-mode class="theme-icon light-icon" />
      <mdui-icon-dark-mode class="theme-icon dark-icon" />
    </mdui-button-icon>
  </mdui-top-app-bar>
</template>

<script setup lang="ts">
import '@mdui/icons/light-mode.js'
import '@mdui/icons/dark-mode.js'
import { getTheme } from 'mdui/functions/getTheme.js'
import { setTheme } from 'mdui/functions/setTheme.js'

import Cookies from 'js-cookie'

import { ref, onMounted } from 'vue'

const theme = ref<'light' | 'dark'>('light')

const toggleTheme = () => {
  let cur_theme = getTheme()
  if (cur_theme === 'light') {
    theme.value = 'dark'
  } else {
    theme.value = 'light'
  }
  setTheme(theme.value)

  changeThemeIcon()

  Cookies.set('theme', theme.value, { expires: 30 })
}

const changeThemeIcon = () => {
  // 图标切换动画通过CSS类控制，不需要手动修改innerHTML
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
  const savedTheme = Cookies.get('theme')
  theme.value = (savedTheme === 'dark' ? 'dark' : 'light')
  setTheme(theme.value)
  changeThemeIcon()
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

.light-icon {
  opacity: 1;
  transform: rotate(0deg) scale(1);
}

.dark-icon {
  opacity: 0;
  transform: rotate(180deg) scale(0.8);
}

/* 图标过渡动画类 */
.theme-icon-transition .theme-icon {
  transition: opacity 150ms cubic-bezier(0.2, 0, 0, 1),
              transform 150ms cubic-bezier(0.2, 0, 0, 1);
}
</style>

<style>
/* 暗色主题时的图标状态 - 非scoped样式以确保全局选择器工作 */
html.mdui-theme-dark .light-icon {
  opacity: 0;
  transform: rotate(-180deg) scale(0.8);
}

html.mdui-theme-dark .dark-icon {
  opacity: 1;
  transform: rotate(0deg) scale(1);
}

/* Top App Bar动画 */
mdui-top-app-bar {
  transition: background-color 150ms cubic-bezier(0.2, 0, 0, 1),
              color 150ms cubic-bezier(0.2, 0, 0, 1);
}
</style>
