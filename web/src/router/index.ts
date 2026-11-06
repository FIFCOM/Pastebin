import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { pageMotion } from '../composables/page-motion'
import {
  DOCS_BASE_PATH,
  DOCS_OVERVIEW_PATH
} from '../content/api-docs'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/PasteEditor.vue'),
    meta: { depth: 0 }
  },
  {
    path: '/join/:pin',
    name: 'JoinLanding',
    component: () => import('../views/PasteEditor.vue'),
    meta: { depth: 0 }
  },
  {
    path: '/p/:paste_id/download/:file_id',
    name: 'FileDownload',
    component: () => import('../views/FileDownload.vue'),
    meta: { depth: 2 }
  },
  {
    path: '/p/:paste_id',
    name: 'PasteViewer',
    component: () => import('../views/PasteViewer.vue'),
    meta: { depth: 1 }
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('../views/UserManagement.vue'),
    meta: { requiresAuth: true, depth: 0 }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue'),
    meta: { depth: 0 }
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: () => import('../views/Favorites.vue'),
    meta: { depth: 0 }
  },
  {
    path: '/collab',
    redirect: '/'
  },
  {
    path: DOCS_BASE_PATH,
    redirect: DOCS_OVERVIEW_PATH
  },
  {
    path: `${DOCS_BASE_PATH}/:section`,
    name: 'ApiDocs',
    component: () => import('../views/ApiDocsView.vue'),
    // 文档各章节之间切换只做淡入淡出,不缩放
    meta: { depth: 0, transition: 'fade' }
  },
  {
    path: '/install',
    name: 'Install',
    component: () => import('../views/Install.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guestOnly: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guestOnly: true }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // 只改 query(如 /users?tab=)不复位滚动
    if (to.path === from.path) return false
    // 等离场动画结束再复位滚动;instant 避免被 scroll-behavior: smooth 变成滚动动画
    return pageMotion
      .afterLeave()
      .then(() => savedPosition ?? { top: 0, left: 0, behavior: 'instant' })
  }
})

// 简单 guestOnly 守卫：已登录用户访问 /login 或 /register 时跳回首页
router.beforeEach(async (to, _from, next) => {
  if (to.path === '/install' || to.path.startsWith('/install/')) {
    next()
    return
  }

  const { isAuthInitialized, initAuth, isLoggedIn } = useAuth()

  if (!isAuthInitialized.value) {
    try {
      await initAuth()
    } catch (e) {
      console.error('Auth init failed in router guard', e)
    }
  }

  if (to.meta.requiresAuth && !isLoggedIn.value) {
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
    return
  }

  if (to.meta.guestOnly && isLoggedIn.value) {
    next({ path: '/' })
  } else {
    next()
  }
})

// 在所有守卫之后解析:被重定向或取消的导航不会遗留状态
router.beforeResolve((to, from) => {
  pageMotion.prepare(to, from)
})

export default router
