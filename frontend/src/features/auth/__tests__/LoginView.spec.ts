import { AxiosError, type AxiosResponse } from 'axios'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import * as api from '@/api/auth'

import LoginView from '../LoginView.vue'

vi.mock('@/api/auth')
const mocked = vi.mocked(api)

const Page = { template: '<div />' }

/** vee-validate debounces schema validation by 5 ms, so wait for a real timer, then settle. */
async function settle(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 10))
  await flushPromises()
}

async function mountLogin(query = '') {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: LoginView },
      { path: '/', name: 'home', component: Page },
      { path: '/account', name: 'account', component: Page },
      { path: '/register', name: 'register', component: Page },
      { path: '/forgot-password', name: 'forgot-password', component: Page },
    ],
  })
  await router.push(`/login${query}`)
  const wrapper = mount(LoginView, { global: { plugins: [router] } })
  return { wrapper, router }
}

async function fill(
  wrapper: Awaited<ReturnType<typeof mountLogin>>['wrapper'],
  email: string,
  password: string,
) {
  const [emailInput, passwordInput] = wrapper.findAll('input')
  await emailInput!.setValue(email)
  await passwordInput!.setValue(password)
  await wrapper.get('form').trigger('submit')
  await settle()
}

function problem(status: number, body: object): AxiosError {
  const response = { status, data: body, headers: {} } as AxiosResponse
  return new AxiosError('fail', String(status), undefined, undefined, response)
}

const user = {
  id: '1',
  email: 'user@example.com',
  role: 'mentee',
  is_active: true,
  is_email_verified: true,
  is_2fa_enabled: false,
  created_at: '2026-11-26T10:00:00Z',
} as const

describe('LoginView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocked.fetchMe.mockResolvedValue(user)
  })

  it('validates before calling the API', async () => {
    const { wrapper } = await mountLogin()

    await fill(wrapper, 'not-an-email', '')

    expect(wrapper.text()).toContain('Enter a valid email address.')
    expect(wrapper.text()).toContain('Enter your password.')
    expect(mocked.login).not.toHaveBeenCalled()
  })

  it('shows the server message for wrong credentials', async () => {
    mocked.login.mockRejectedValue(
      problem(401, { code: 'invalid_credentials', detail: 'Incorrect email or password.' }),
    )
    const { wrapper } = await mountLogin()

    await fill(wrapper, 'user@example.com', 'wrong')

    expect(wrapper.get('[role=alert]').text()).toBe('Incorrect email or password.')
  })

  it('goes to the redirect target after login, but only for same-site paths', async () => {
    mocked.login.mockResolvedValue({
      status: 'authenticated',
      access_token: 'a',
      token_type: 'bearer',
      expires_in: 900,
    })
    const { wrapper, router } = await mountLogin('?redirect=/account')

    await fill(wrapper, 'user@example.com', 'pw')

    expect(router.currentRoute.value.name).toBe('account')
  })

  it('ignores an external redirect', async () => {
    mocked.login.mockResolvedValue({
      status: 'authenticated',
      access_token: 'a',
      token_type: 'bearer',
      expires_in: 900,
    })
    const { wrapper, router } = await mountLogin('?redirect=//evil.example')

    await fill(wrapper, 'user@example.com', 'pw')

    expect(router.currentRoute.value.name).toBe('home')
  })

  it('asks for the emailed code when 2FA is on', async () => {
    mocked.login.mockResolvedValue({ status: 'otp_required', challenge_id: 'c1', expires_in: 600 })
    mocked.verifyOtp.mockRejectedValueOnce(
      problem(401, { code: 'invalid_otp', detail: 'The code is incorrect.', attempts_left: 4 }),
    )
    const { wrapper } = await mountLogin()

    await fill(wrapper, 'user@example.com', 'pw')
    expect(wrapper.text()).toContain('Enter your login code')

    await wrapper.get('input').setValue('123456')
    await wrapper.get('form').trigger('submit')
    await settle()

    expect(mocked.verifyOtp).toHaveBeenCalledWith('c1', '123456')
    expect(wrapper.get('[role=alert]').text()).toBe('The code is incorrect. Attempts left: 4.')
  })

  it('explains why the user landed here after an inactivity logout', async () => {
    const { wrapper } = await mountLogin('?reason=inactivity')

    expect(wrapper.text()).toContain('logged out after a period of inactivity')
  })
})
