import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'

import { useInactivityTimer } from '../useInactivityTimer'

const MINUTE = 60_000

function start(onTimeout = vi.fn<() => void>()) {
  const scope = effectScope()
  const timer = scope.run(() =>
    useInactivityTimer({ onTimeout, timeoutMs: 15 * MINUTE, warningMs: 2 * MINUTE }),
  )!
  return { timer, onTimeout, stop: () => scope.stop() }
}

describe('useInactivityTimer', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('warns 2 minutes before the timeout and logs out at the timeout', () => {
    const { timer, onTimeout, stop } = start()

    vi.advanceTimersByTime(12 * MINUTE)
    expect(timer.showWarning.value).toBe(false)

    vi.advanceTimersByTime(1 * MINUTE + 1000)
    expect(timer.showWarning.value).toBe(true)
    expect(timer.secondsLeft.value).toBeLessThanOrEqual(120)

    vi.advanceTimersByTime(2 * MINUTE)
    expect(onTimeout).toHaveBeenCalledOnce()

    vi.advanceTimersByTime(5 * MINUTE)
    expect(onTimeout).toHaveBeenCalledOnce()
    stop()
  })

  it('resets on keyboard, mouse and scroll activity', () => {
    const { timer, onTimeout, stop } = start()

    for (const event of ['keydown', 'mousemove', 'scroll']) {
      vi.advanceTimersByTime(10 * MINUTE)
      window.dispatchEvent(new Event(event))
    }
    vi.advanceTimersByTime(10 * MINUTE)

    expect(timer.showWarning.value).toBe(false)
    expect(onTimeout).not.toHaveBeenCalled()
    stop()
  })

  it('ignores passive activity during the warning; only "stay" dismisses it', () => {
    const { timer, onTimeout, stop } = start()
    vi.advanceTimersByTime(14 * MINUTE)
    expect(timer.showWarning.value).toBe(true)

    window.dispatchEvent(new Event('mousemove'))
    expect(timer.showWarning.value).toBe(true)

    timer.stayActive()
    expect(timer.showWarning.value).toBe(false)
    vi.advanceTimersByTime(10 * MINUTE)
    expect(onTimeout).not.toHaveBeenCalled()
    stop()
  })

  it('stops listening when its scope is disposed', () => {
    const { onTimeout, stop } = start()

    stop()
    vi.advanceTimersByTime(60 * MINUTE)

    expect(onTimeout).not.toHaveBeenCalled()
  })
})
