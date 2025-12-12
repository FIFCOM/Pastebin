<template>
  <GlobalHeader></GlobalHeader>
  <mdui-layout>
    <mdui-layout-main class="mdui-container">
      <router-view />
    </mdui-layout-main>
  </mdui-layout>
  <GlobalFooter></GlobalFooter>
</template>

<script setup lang="ts">
import 'mdui/mdui.css'
import 'mdui'

import { onMounted } from 'vue'
import GlobalHeader from './components/GlobalHeader.vue'
import GlobalFooter from './components/GlobalFooter.vue'
import { useAuth } from './composables/useAuth'

const { initAuth } = useAuth()

onMounted(() => {
  initAuth().catch((e) => {
    console.error('Failed to initialize auth on app mount', e)
  })
})
</script>

<style scoped>
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
