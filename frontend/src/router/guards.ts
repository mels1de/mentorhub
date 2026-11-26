import type { NavigationGuardWithThis, RouteLocationRaw } from 'vue-router'

import type { UserRole } from '@/api/auth'
import type { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    /** Only for logged-in users; others go to the login page and come back afterwards. */
    requiresAuth?: boolean
    /** Logged-in users without one of these roles see the forbidden page. */
    roles?: UserRole[]
    /** Login, register...: a logged-in user is sent home instead. */
    guestOnly?: boolean
  }
}

type AuthStore = ReturnType<typeof useAuthStore>

export function createAuthGuard(auth: AuthStore): NavigationGuardWithThis<undefined> {
  return async (to): Promise<true | RouteLocationRaw> => {
    // The first navigation waits for the refresh cookie to be tried, so a reload doesn't
    // bounce a logged-in user to the login page.
    await auth.bootstrap()

    if (to.meta.guestOnly && auth.isAuthenticated) return { name: 'home' }
    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (to.meta.roles && !auth.hasRole(...to.meta.roles)) return { name: 'forbidden' }
    return true
  }
}
