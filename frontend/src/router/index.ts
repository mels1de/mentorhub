import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: { name: 'status' } },
    {
      path: '/status',
      name: 'status',
      component: () => import('@/features/status/StatusView.vue'),
    },
  ],
})

export default router
