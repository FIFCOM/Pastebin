<script setup lang="ts">
// app-motion-system / PageTransition.vue
// 放在页面视口容器里,替代裸 <RouterView />。
// - animating:动画进行中,外层容器据此加 data-animating(横向位移时裁掉溢出)。
// - enter:新页面即将插入,外层容器据此更新随路由变化的布局属性(如页面宽度),
//   这样离场页面不会在动画途中被突然改宽。
import { pageMotion } from "./page-motion" // TODO(adapt): 按实际路径

const emit = defineEmits<{ animating: [value: boolean]; enter: [] }>()

function onBeforeLeave(): void {
  emit("animating", true)
}
function onBeforeEnter(): void {
  pageMotion.beginEnter() // 必须在这里开错峰窗口:此刻旧页面已被移除
  emit("animating", true)
  emit("enter")
}
function onSettled(): void {
  pageMotion.leaveDone()
  emit("animating", false)
}
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <Transition
      name="page"
      mode="out-in"
      @before-leave="onBeforeLeave"
      @after-leave="pageMotion.leaveDone()"
      @leave-cancelled="onSettled"
      @before-enter="onBeforeEnter"
      @after-enter="onSettled"
      @enter-cancelled="onSettled"
    >
      <!-- key 用 path 不用 fullPath:只改 query 不触发页面过渡 -->
      <component :is="Component" :key="route.path" />
    </Transition>
  </RouterView>
</template>
