import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type RouteRecordRaw } from 'vue-router'

import type { User } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

import { createAuthGuard } from '../guards'

vi.mock('@/api/auth')

const Page = { template: '<div />' }
const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: Page, meta: { requiresAuth: true } },
  { path: '/login', name: 'login', component: Page, meta: { guestOnly: true } },
  {
    path: '/admin',
    name: 'admin',
    component: Page,
    meta: { requiresAuth: true, roles: ['admin'] },
  },
  { path: '/forbidden', name: 'forbidden', component: Page },
  { path: '/status', name: 'status', component: Page },
]

function setup(user: Partial<User> | null) {
  setActivePinia(createPinia())
  const auth = useAuthStore()
  vi.spyOn(auth, 'bootstrap').mockResolvedValue()
  if (user) {
    auth.accessToken = 'token'
    auth.user = { role: 'mentee', ...user } as User
  }
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.beforeEach(createAuthGuard(auth))
  return router
}

describe('auth guard', () => {
  beforeEach(() => vi.resetAllMocks())

  it('sends anonymous users to login and remembers where they wanted to go', async () => {
    const router = setup(null)

    await router.push('/admin?tab=2')

    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/admin?tab=2')
  })

  it('lets anonymous users open public pages', async () => {
    const router = setup(null)

    await router.push('/status')

    expect(router.currentRoute.value.name).toBe('status')
  })

  it('shows forbidden for a missing role', async () => {
    const router = setup({ role: 'mentor' })

    await router.push('/admin')

    expect(router.currentRoute.value.name).toBe('forbidden')
  })

  it('lets an admin in', async () => {
    const router = setup({ role: 'admin' })

    await router.push('/admin')

    expect(router.currentRoute.value.name).toBe('admin')
  })

  it('keeps logged-in users away from the login page', async () => {
    const router = setup({ role: 'mentee' })

    await router.push('/login')

    expect(router.currentRoute.value.name).toBe('home')
  })
})
