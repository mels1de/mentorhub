import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as api from '@/api/auth'
import type { OtpChallenge, User, UserRole } from '@/api/auth'
import { openTabChannel, withTabLock, type TabMessage } from '@/lib/tabs'

export type LoginResult = { status: 'authenticated' } | OtpChallenge

/**
 * The session. The access token lives only in memory (never localStorage, so XSS can't
 * read it); after a reload it is restored from the httpOnly refresh cookie.
 */
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => accessToken.value !== null && user.value !== null)

  let refreshing: Promise<string | null> | null = null
  let bootstrapping: Promise<void> | null = null

  const tabs = openTabChannel('mentorhub-auth', onTabMessage)

  /** Single-flight in this tab, and serialized across tabs: they share one refresh cookie. */
  function refreshAccessToken(): Promise<string | null> {
    refreshing ??= withTabLock('mentorhub-auth-refresh', async () => {
      try {
        accessToken.value = (await api.refresh()).access_token
        return accessToken.value
      } catch {
        return null
      }
    }).finally(() => {
      refreshing = null
    })
    return refreshing
  }

  /** Restore the session on page load; resolves once we know whether the user is logged in. */
  function bootstrap(): Promise<void> {
    bootstrapping ??= (async () => {
      if (await refreshAccessToken()) await loadUser()
    })()
    return bootstrapping
  }

  async function loadUser(): Promise<void> {
    try {
      user.value = await api.fetchMe()
    } catch {
      clear()
    }
  }

  async function startSession(token: string): Promise<void> {
    accessToken.value = token
    await loadUser()
    tabs.post({ type: 'login' })
  }

  async function login(email: string, password: string): Promise<LoginResult> {
    const result = await api.login(email, password)
    if (result.status === 'otp_required') return result
    await startSession(result.access_token)
    return { status: 'authenticated' }
  }

  async function completeOtp(challengeId: string, code: string): Promise<void> {
    await startSession((await api.verifyOtp(challengeId, code)).access_token)
  }

  async function logout(): Promise<void> {
    try {
      await api.logout()
    } finally {
      clear()
      tabs.post({ type: 'logout' })
    }
  }

  async function logoutEverywhere(): Promise<void> {
    await api.logoutEverywhere()
    clear()
    tabs.post({ type: 'logout' })
  }

  function clear(): void {
    accessToken.value = null
    user.value = null
  }

  function hasRole(...roles: UserRole[]): boolean {
    return user.value !== null && roles.includes(user.value.role)
  }

  function onTabMessage(message: TabMessage): void {
    if (message.type === 'logout') clear()
    if (message.type === 'login' && !isAuthenticated.value) {
      bootstrapping = null
      void bootstrap()
    }
  }

  return {
    accessToken,
    user,
    isAuthenticated,
    bootstrap,
    refreshAccessToken,
    loadUser,
    login,
    completeOtp,
    logout,
    logoutEverywhere,
    clear,
    hasRole,
    broadcast: tabs.post,
  }
})
