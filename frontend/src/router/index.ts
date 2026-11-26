import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/features/home/HomeView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/features/auth/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/features/auth/RegisterView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('@/features/auth/ForgotPasswordView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('@/features/auth/ResetPasswordView.vue'),
    },
    {
      path: '/verify-email',
      name: 'verify-email',
      component: () => import('@/features/auth/VerifyEmailView.vue'),
    },
    {
      path: '/account',
      name: 'account',
      component: () => import('@/features/account/AccountView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/features/admin/AdminUsersView.vue'),
      meta: { requiresAuth: true, roles: ['admin'] },
    },
    {
      path: '/forbidden',
      name: 'forbidden',
      component: () => import('@/features/errors/ForbiddenView.vue'),
    },
    {
      path: '/status',
      name: 'status',
      component: () => import('@/features/status/StatusView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/features/errors/NotFoundView.vue'),
    },
  ],
})

export default router
