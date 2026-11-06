# Vue 3 + vue-router 4 接入

按顺序接。每一步都能单独验证。

## 1. 入口

```ts
// main.ts
import "./styles/motion.css" // 放在组件库样式之后、业务样式之前
import { pageMotion } from "./composables/page-motion"

pageMotion.init() // 必须在 mount 之前
createApp(App).use(router).mount("#app")
```

如果样式经 `index.css` 汇总,在 `@import` 列表里让 `motion.css` 排在 `base` 之后、各页面样式之前,这样页面样式里已有的旧令牌(如 `--xx-fast`、`--xx-ease`)可以别名到它的 `--m-*`。

## 2. 路由

```ts
import { pageMotion } from "../composables/page-motion"

const router = createRouter({
  history,
  scrollBehavior(to, from, saved) {
    if (to.path === from.path) return false
    // 等离场动画结束再复位滚动;instant 避免被全局 scroll-behavior: smooth 变成滚动动画
    return pageMotion.afterLeave().then(() => saved ?? { top: 0, left: 0, behavior: "instant" })
  },
  routes: [
    { path: "/home", component: Home, meta: { depth: 0 } },
    { path: "/items", component: Items, meta: { depth: 0 } },
    { path: "/items/:id", component: Item, meta: { depth: 1 } },
    { path: "/items/new", component: ItemForm, meta: { depth: 1, transition: "shared-y" } },
    { path: "/home-with-fab", component: Fab, meta: { depth: 0, transition: "fade" } },
    { path: "/login", component: Login }, // 没有 depth → fade
  ],
})

// 在所有守卫之后解析:被重定向或取消的导航不会遗留状态
router.beforeResolve((to, from) => {
  pageMotion.prepare(to, from)
})
```

要点:

- 用 `beforeResolve`,不用 `beforeEach`。`beforeEach` 里的守卫可能还会重定向。
- `RouteMeta` 的类型扩展已在 `page-motion.ts` 里声明,不要在路由文件里重复声明同名字段。
- 守卫在 `beforeResolve` 之前取消导航(比如未保存提示),`<html>` 上可能留着旧的预设。下一次导航会重新解析并覆盖,没有副作用。
- 想让某次跳转用特定预设:`pageMotion.next("fade"); router.push(...)`。

## 3. 外壳

```vue
<script setup lang="ts">
import { ref } from "vue"
import { useRoute } from "vue-router"
import PageTransition from "./PageTransition.vue"

const route = useRoute()
// 随路由变化的布局属性(这里是页面宽度)在新页面进入时才更新,
// 否则离场页面会在动画途中被突然改宽
const width = ref(route.meta.width ?? "full")
const animating = ref(false)
</script>
<template>
  <main class="main-content" :data-page-animating="animating || undefined">
    <div class="page-container" :data-width="width">
      <PageTransition @animating="animating = $event" @enter="width = route.meta.width ?? 'full'" />
    </div>
  </main>
</template>
```

页面组件必须只有**一个根元素**,`<Transition>` 才能对它加类名。

## 4. 登录页与主界面互切(App 根部)

```vue
<script setup lang="ts">
import { computed, h } from "vue"
import { RouterView, useRoute } from "vue-router"
import { pageMotion } from "./composables/page-motion"
import AppShell from "./components/AppShell.vue"

const route = useRoute()
const showLogin = computed(() => route.path === "/login" || !auth.isAuthenticated.value)

// 登录页的宿主,原因见 pitfalls.md“页面区域为空”
const LoginHost = () => h(RouterView)
</script>

<template>
  <Transition name="shell-fade" mode="out-in" @before-enter="pageMotion.beginEnter()">
    <LoginHost v-if="showLogin" key="login" />
    <AppShell v-else key="shell" />
  </Transition>
</template>
```

## 5. 设置页入口(三档单选)

```vue
<script setup lang="ts">
import { pageMotion, type MotionLevel } from "./page-motion"
const levels: { value: MotionLevel; label: string }[] = [
  { value: "full", label: "完整" },
  { value: "reduced", label: "精简" },
  { value: "off", label: "关闭" },
]
</script>
<template>
  <div role="radiogroup" aria-label="动画效果">
    <label v-for="o in levels" :key="o.value">
      <input type="radio" name="motion" :checked="pageMotion.level.value === o.value"
             @change="pageMotion.setLevel(o.value)" />{{ o.label }}
    </label>
  </div>
  <p>精简只保留淡入淡出,关闭则不播放任何动画。系统开启“减少动态效果”时始终关闭。</p>
</template>
```

选项文案要写明系统设置优先,否则用户在系统里开了减少动态效果、应用里选“完整”却没动画会困惑。

## 6. 错峰容器

```vue
<section class="page" data-stagger>   <!-- 直接子元素依次上浮淡入 -->
  <header>…</header>
  <Card /><Card /><Card />
</section>
```

只放在结构容器上。会随筛选、分页变化的数据列表继续用 `<TransitionGroup>`。

## 7. JS 调用点

```ts
if (!pageMotion.allowsFullMotion()) return        // 数字滚动、高度补间:直接给终值
el.scrollIntoView({ behavior: pageMotion.allowsFullMotion() ? "smooth" : "auto", block: "start" })
```

## 8. 测试环境

jsdom 没有 `scrollTo`,`scrollBehavior` 会调用它。在 vitest 的 setup 文件里补桩:

```ts
beforeEach(() => { window.scrollTo = vi.fn() as typeof window.scrollTo })
```

`matchMedia` 在 jsdom 里默认也不存在,`page-motion.ts` 已用 `typeof matchMedia === "function"` 守卫。要测系统设置分支时用 `vi.stubGlobal("matchMedia", …)`(见 `templates/page-motion.test.ts`)。
