import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

// 路由与守卫约定见 docs/system-design.md 11.2
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true }
    },
    {
      path: '/',
      redirect: '/books'
    },
    {
      path: '/books',
      name: 'books',
      component: () => import('@/views/BooksView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/readers',
      name: 'readers',
      component: () => import('@/views/ReadersView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/borrows',
      name: 'borrows',
      component: () => import('@/views/BorrowsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('@/views/UsersView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { public: true }
    }
  ]
})

/** redirect 仅接受站内绝对路径，避免开放重定向 */
function isSafeRedirect(value: unknown): value is string {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
}

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    // 有 token 但尚未加载用户信息时，先拉取当前操作员
    if (authStore.user === null) {
      try {
        await authStore.fetchMe()
      } catch {
        // fetchMe 失败（如 token 失效）时拦截器已清理状态
        return { path: '/login', query: { redirect: to.fullPath } }
      }
    }
    return true
  }

  if (to.path === '/login' && authStore.isAuthenticated) {
    return isSafeRedirect(to.query.redirect) ? to.query.redirect : '/books'
  }

  return true
})

export { isSafeRedirect }
export default router
