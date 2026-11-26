import { computed, onScopeDispose, ref } from 'vue'

import { openTabChannel } from '@/lib/tabs'

export const INACTIVITY_TIMEOUT_MS = 15 * 60_000
export const INACTIVITY_WARNING_MS = 2 * 60_000

const ACTIVITY_EVENTS = ['mousemove', 'pointerdown', 'keydown', 'wheel', 'touchstart', 'scroll']
// Mousemove fires dozens of times a second; one timestamp per second is plenty.
const THROTTLE_MS = 1_000
const TICK_MS = 1_000

export interface InactivityOptions {
  onTimeout: () => void
  timeoutMs?: number
  warningMs?: number
}

/**
 * Logs the user out after `timeoutMs` without mouse, keyboard, scroll or touch activity in
 * any tab. For the last `warningMs` a warning is shown; then only an explicit "stay" counts,
 * so a mouse twitch doesn't silently dismiss it.
 */
export function useInactivityTimer(options: InactivityOptions) {
  const timeoutMs = options.timeoutMs ?? INACTIVITY_TIMEOUT_MS
  const warningMs = options.warningMs ?? INACTIVITY_WARNING_MS

  const lastActivity = ref(Date.now())
  const now = ref(Date.now())
  let timedOut = false

  const remainingMs = computed(() => Math.max(0, lastActivity.value + timeoutMs - now.value))
  const showWarning = computed(() => remainingMs.value <= warningMs)
  const secondsLeft = computed(() => Math.ceil(remainingMs.value / 1000))

  // Other tabs count as activity: working in one tab must not log out the others.
  const tabs = openTabChannel('mentorhub-activity', (message) => {
    if (message.type === 'activity' && message.at > lastActivity.value) {
      lastActivity.value = message.at
      now.value = Date.now()
    }
  })

  function markActive(): void {
    lastActivity.value = Date.now()
    now.value = lastActivity.value
    tabs.post({ type: 'activity', at: lastActivity.value })
  }

  function onActivity(): void {
    if (showWarning.value || Date.now() - lastActivity.value < THROTTLE_MS) return
    markActive()
  }

  function check(): void {
    now.value = Date.now()
    if (remainingMs.value === 0 && !timedOut) {
      timedOut = true
      options.onTimeout()
    }
  }

  // Background tabs throttle timers to once a minute or less: re-check as soon as it's visible.
  function onVisibilityChange(): void {
    if (document.visibilityState === 'visible') check()
  }

  for (const event of ACTIVITY_EVENTS) {
    window.addEventListener(event, onActivity, { passive: true, capture: true })
  }
  document.addEventListener('visibilitychange', onVisibilityChange)
  const timer = window.setInterval(check, TICK_MS)

  onScopeDispose(() => {
    for (const event of ACTIVITY_EVENTS) {
      window.removeEventListener(event, onActivity, { capture: true })
    }
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.clearInterval(timer)
    tabs.close()
  })

  return { showWarning, secondsLeft, stayActive: markActive }
}
