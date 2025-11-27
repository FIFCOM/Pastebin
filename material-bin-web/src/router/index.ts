import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/PasteEditor.vue')
  },
  {
    path: '/p/:paste_id',
    name: 'PasteViewer',
    component: () => import('../views/PasteViewer.vue')
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
  routes
})

// 简单 guestOnly 守卫：已登录用户访问 /login 或 /register 时跳回首页
router.beforeEach(async (to, from, next) => {
  const { isAuthInitialized, initAuth, isLoggedIn } = useAuth()

  if (!isAuthInitialized.value) {
    try {
      await initAuth()
    } catch (e) {
      console.error('Auth init failed in router guard', e)
    }
  }

  if (to.meta.guestOnly && isLoggedIn.value) {
    next({ path: '/' })
  } else {
    next()
  }
})

export default router