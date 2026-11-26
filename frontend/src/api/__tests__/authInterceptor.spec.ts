import axios, { AxiosError, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios'
import { describe, expect, it, vi } from 'vitest'

import { installAuthInterceptors, type AuthHooks } from '../authInterceptor'

type Reply = { status: number; data?: unknown }

/** An axios instance whose "server" answers from `handler`, recording each request. */
function setup(handler: (config: InternalAxiosRequestConfig) => Reply) {
  const seen: { url?: string; auth?: string }[] = []
  const adapter: AxiosAdapter = async (config) => {
    seen.push({ url: config.url, auth: config.headers.get('Authorization')?.toString() })
    const { status, data } = handler(config)
    const response = { data, status, statusText: '', headers: {}, config }
    if (status >= 400) {
      throw new AxiosError('fail', String(status), config, undefined, response)
    }
    return response
  }
  const http = axios.create({ adapter })
  let token: string | null = 'old'
  const hooks: AuthHooks = {
    getToken: () => token,
    refresh: vi.fn<() => Promise<string | null>>(async () => {
      token = 'new'
      return token
    }),
    onSessionExpired: vi.fn<() => void>(),
  }
  installAuthInterceptors(http, hooks)
  return { http, hooks, seen }
}

const expired: Reply = { status: 401, data: { code: 'invalid_token' } }
const ok: Reply = { status: 200, data: 'ok' }

describe('auth interceptor', () => {
  it('sends the access token as a Bearer header', async () => {
    const { http, seen } = setup(() => ok)

    await http.get('/users/me')

    expect(seen[0]?.auth).toBe('Bearer old')
  })

  it('refreshes once on an expired token and replays the request', async () => {
    const { http, hooks, seen } = setup((config) =>
      config.headers.get('Authorization') === 'Bearer old' ? expired : ok,
    )

    const response = await http.get('/users/me')

    expect(response.data).toBe('ok')
    expect(hooks.refresh).toHaveBeenCalledOnce()
    expect(seen.map((r) => r.auth)).toEqual(['Bearer old', 'Bearer new'])
  })

  it('shares one refresh between parallel requests', async () => {
    const { http, hooks } = setup((config) =>
      config.headers.get('Authorization') === 'Bearer old' ? expired : ok,
    )
    let refreshes = 0
    let pending: Promise<string> | null = null
    hooks.refresh = vi.fn<() => Promise<string | null>>(() => {
      pending ??= new Promise((resolve) => {
        refreshes++
        setTimeout(() => resolve('new'), 0)
      })
      return pending
    })

    await Promise.all([http.get('/a'), http.get('/b'), http.get('/c')])

    expect(refreshes).toBe(1)
  })

  it('gives up and reports the session as expired when refresh fails', async () => {
    const { http, hooks } = setup(() => expired)
    hooks.refresh = vi.fn<() => Promise<string | null>>(async () => null)

    await expect(http.get('/users/me')).rejects.toBeInstanceOf(AxiosError)
    expect(hooks.onSessionExpired).toHaveBeenCalledOnce()
  })

  it('does not retry forever when the new token is rejected too', async () => {
    const { http, hooks, seen } = setup(() => expired)

    await expect(http.get('/users/me')).rejects.toBeInstanceOf(AxiosError)
    expect(hooks.refresh).toHaveBeenCalledOnce()
    expect(seen).toHaveLength(2)
  })

  it.each([
    ['wrong password', { status: 401, data: { code: 'invalid_credentials' } }],
    ['wrong login code', { status: 401, data: { code: 'invalid_otp' } }],
    ['forbidden', { status: 403, data: { code: 'permission_denied' } }],
  ])('passes a %s error straight to the caller', async (_, reply) => {
    const { http, hooks } = setup(() => reply)

    await expect(http.post('/auth/login')).rejects.toBeInstanceOf(AxiosError)
    expect(hooks.refresh).not.toHaveBeenCalled()
  })

  it('never refreshes because the refresh call itself failed', async () => {
    const { http, hooks } = setup(() => expired)

    await expect(http.post('/auth/refresh')).rejects.toBeInstanceOf(AxiosError)
    expect(hooks.refresh).not.toHaveBeenCalled()
  })
})
