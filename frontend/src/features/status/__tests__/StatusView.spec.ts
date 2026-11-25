import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchReadiness, type Readiness } from '@/api/health'

import StatusView from '../StatusView.vue'
import { READINESS_POLL_MS } from '../useReadiness'

vi.mock('@/api/health', () => ({ fetchReadiness: vi.fn<typeof fetchReadiness>() }))
const fetchMock = vi.mocked(fetchReadiness)

const healthy: Readiness = { status: 'pass', checks: { database: 'pass', redis: 'pass' } }
const redisDown: Readiness = { status: 'fail', checks: { database: 'pass', redis: 'fail' } }

function mountView() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return mount(StatusView, { global: { plugins: [[VueQueryPlugin, { queryClient }]] } })
}

describe('StatusView', () => {
  beforeEach(() => {
    fetchMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows "checking" until the first response arrives', () => {
    fetchMock.mockReturnValue(new Promise(() => {}))

    const wrapper = mountView()

    expect(wrapper.get('[data-testid=overall]').attributes('data-state')).toBe('checking')
  })

  it('shows operational when every check passes', async () => {
    fetchMock.mockResolvedValue(healthy)

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.get('[data-testid=overall]').attributes('data-state')).toBe('up')
    expect(wrapper.get('[data-testid=check-redis]').text()).toContain('pass')
  })

  it('shows degraded and the failing check on a 503 report', async () => {
    fetchMock.mockResolvedValue(redisDown)

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.get('[data-testid=overall]').attributes('data-state')).toBe('degraded')
    expect(wrapper.get('[data-testid=check-redis]').text()).toContain('fail')
  })

  it('shows unreachable when the request fails, hiding the stale report', async () => {
    vi.useFakeTimers()
    fetchMock.mockResolvedValueOnce(healthy).mockRejectedValueOnce(new Error('Network Error'))

    const wrapper = mountView()
    await flushPromises()
    await vi.advanceTimersByTimeAsync(READINESS_POLL_MS)
    await flushPromises()

    expect(wrapper.get('[data-testid=overall]').attributes('data-state')).toBe('down')
    expect(wrapper.find('[data-testid=check-redis]').exists()).toBe(false)
  })

  it('polls again after the interval', async () => {
    vi.useFakeTimers()
    fetchMock.mockResolvedValueOnce(healthy).mockResolvedValueOnce(redisDown)

    const wrapper = mountView()
    await flushPromises()
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(READINESS_POLL_MS)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(wrapper.get('[data-testid=overall]').attributes('data-state')).toBe('degraded')
  })
})
