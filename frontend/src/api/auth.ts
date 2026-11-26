import type { components } from './schema'
import { http } from './http'

type Schemas = components['schemas']

export type User = Schemas['UserRead']
export type UserRole = User['role']
export type TokenResponse = Schemas['TokenResponse']
export type OtpChallenge = Schemas['OtpChallengeResponse']
export type LoginResponse = Schemas['LoginResponse']
export type RegisterRequest = Schemas['RegisterRequest']
export type UserPage = Schemas['Page_UserRead_']

// Auth endpoints must never trigger the refresh-and-retry interceptor (it would loop).
export const AUTH_PREFIX = '/auth/'

export async function register(body: RegisterRequest): Promise<User> {
  return (await http.post<User>('/auth/register', body)).data
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return (await http.post<LoginResponse>('/auth/login', { email, password })).data
}

export async function verifyOtp(challengeId: string, code: string): Promise<TokenResponse> {
  const body = { challenge_id: challengeId, code }
  return (await http.post<TokenResponse>('/auth/2fa/verify', body)).data
}

export async function resendOtp(challengeId: string): Promise<void> {
  await http.post('/auth/2fa/resend', { challenge_id: challengeId })
}

export async function refresh(): Promise<TokenResponse> {
  return (await http.post<TokenResponse>('/auth/refresh')).data
}

export async function logout(): Promise<void> {
  await http.post('/auth/logout')
}

export async function logoutEverywhere(): Promise<void> {
  await http.post('/auth/logout-all')
}

export async function verifyEmail(token: string): Promise<void> {
  await http.post('/auth/verify-email', { token })
}

export async function resendVerification(): Promise<void> {
  await http.post('/auth/verify-email/resend')
}

export async function requestPasswordReset(email: string): Promise<void> {
  await http.post('/auth/password-reset', { email })
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  await http.post('/auth/password-reset/confirm', { token, new_password: newPassword })
}

export async function setTwoFactor(enabled: boolean, password: string): Promise<void> {
  await http.post(enabled ? '/auth/2fa/enable' : '/auth/2fa/disable', { password })
}

export async function fetchMe(): Promise<User> {
  return (await http.get<User>('/users/me')).data
}

export async function fetchUsers(page: number, size: number): Promise<UserPage> {
  return (await http.get<UserPage>('/users', { params: { page, size } })).data
}
