import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/api/auth'
import type { User } from '@/api/auth'

import { useAuthStore } from '../auth'

vi.mock('@/api/auth')
const mocked = vi.mocked(api)

const user: User = {
  id: '01a2',
  email: 'user@example.com',
  role: 'mentee',
  is_active: true,
  is_email_verified: true,
  is_2fa_enabled: false,
  created_at: '2026-11-26T10:00:00Z',
}
const tokens = {
  status: 'authenticated',
  access_token: 'access',
  token_type: 'bearer',
  expires_in: 900,
} as const

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    mocked.fetchMe.mockResolvedValue(user)
  })

  it('logs in without 2FA', async () => {
    mocked.login.mockResolvedValue(tokens)
    const auth = useAuthStore()

    await expect(auth.login('user@example.com', 'pw')).resolves.toEqual({ status: 'authenticated' })

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.accessToken).toBe('access')
    expect(auth.user?.email).toBe('user@example.com')
  })

  it('stops at the OTP step when 2FA is on, then completes it', async () => {
    const challenge = { status: 'otp_required', challenge_id: 'c1', expires_in: 600 } as const
    mocked.login.mockResolvedValue(challenge)
    mocked.verifyOtp.mockResolvedValue(tokens)
    const auth = useAuthStore()

    await expect(auth.login('user@example.com', 'pw')).resolves.toEqual(challenge)
    expect(auth.isAuthenticated).toBe(false)

    await auth.completeOtp('c1', '123456')
    expect(mocked.verifyOtp).toHaveBeenCalledWith('c1', '123456')
    expect(auth.isAuthenticated).toBe(true)
  })

  it('restores the session from the refresh cookie on bootstrap', async () => {
    mocked.refresh.mockResolvedValue(tokens)
    const auth = useAuthStore()

    await auth.bootstrap()
    await auth.bootstrap()

    expect(mocked.refresh).toHaveBeenCalledOnce()
    expect(auth.isAuthenticated).toBe(true)
  })

  it('stays anonymous when there is no valid refresh cookie', async () => {
    mocked.refresh.mockRejectedValue(new Error('401'))
    const auth = useAuthStore()

    await auth.bootstrap()

    expect(auth.isAuthenticated).toBe(false)
    expect(mocked.fetchMe).not.toHaveBeenCalled()
  })

  it('runs one refresh for many concurrent callers', async () => {
    let resolve!: (value: typeof tokens) => void
    mocked.refresh.mockReturnValue(new Promise((r) => (resolve = r)))
    const auth = useAuthStore()

    const calls = [auth.refreshAccessToken(), auth.refreshAccessToken(), auth.refreshAccessToken()]
    resolve(tokens)

    expect(await Promise.all(calls)).toEqual(['access', 'access', 'access'])
    expect(mocked.refresh).toHaveBeenCalledOnce()
  })

  it('clears the session on logout even if the request fails', async () => {
    mocked.login.mockResolvedValue(tokens)
    mocked.logout.mockRejectedValue(new Error('network'))
    const auth = useAuthStore()
    await auth.login('user@example.com', 'pw')

    await expect(auth.logout()).rejects.toThrow('network')

    expect(auth.isAuthenticated).toBe(false)
    expect(auth.accessToken).toBeNull()
  })

  it('checks roles', async () => {
    mocked.login.mockResolvedValue(tokens)
    const auth = useAuthStore()
    expect(auth.hasRole('mentee')).toBe(false)

    await auth.login('user@example.com', 'pw')

    expect(auth.hasRole('mentee', 'mentor')).toBe(true)
    expect(auth.hasRole('admin')).toBe(false)
  })
})
