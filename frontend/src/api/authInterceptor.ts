import { isAxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

export interface AuthHooks {
  getToken(): string | null
  /** Resolve with a fresh access token, or null when the session is over. Must be single-flight. */
  refresh(): Promise<string | null>
  onSessionExpired(): void
}

type RetriableConfig = InternalAxiosRequestConfig & { _authRetried?: boolean }

const REFRESH_URL = '/auth/refresh'

function isExpiredAccessToken(data: unknown): boolean {
  // Only `invalid_token` means "your access token is missing or expired". A 401 with
  // `invalid_credentials` (wrong password) or `invalid_otp` must reach the form untouched.
  return (
    typeof data === 'object' && data !== null && 'code' in data && data.code === 'invalid_token'
  )
}

/**
 * Bearer header on every request; on an expired access token refresh once and replay the
 * request. Parallel 401s share one refresh because `hooks.refresh` is single-flight.
 */
export function installAuthInterceptors(http: AxiosInstance, hooks: AuthHooks): () => void {
  const request = http.interceptors.request.use((config) => {
    const token = hooks.getToken()
    if (token && !config.headers.has('Authorization')) {
      config.headers.set('Authorization', `Bearer ${token}`)
    }
    return config
  })

  const response = http.interceptors.response.use(undefined, async (error: unknown) => {
    if (!isAxiosError(error) || !error.config || error.response?.status !== 401) throw error
    const config = error.config as RetriableConfig
    if (config._authRetried || config.url === REFRESH_URL) throw error
    if (!isExpiredAccessToken(error.response.data)) throw error

    config._authRetried = true
    const token = await hooks.refresh()
    if (!token) {
      hooks.onSessionExpired()
      throw error
    }
    config.headers.set('Authorization', `Bearer ${token}`)
    return http.request(config)
  })

  return () => {
    http.interceptors.request.eject(request)
    http.interceptors.response.eject(response)
  }
}
