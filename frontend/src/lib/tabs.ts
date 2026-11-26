/** Run `task` while holding a lock shared by every tab of this origin (Web Locks API). */
export async function withTabLock<T>(name: string, task: () => Promise<T>): Promise<T> {
  if (typeof navigator === 'undefined' || !('locks' in navigator)) return task()
  return navigator.locks.request(name, task)
}

export type TabMessage = { type: 'login' } | { type: 'logout' } | { type: 'activity'; at: number }

export interface TabChannel {
  post(message: TabMessage): void
  close(): void
}

/** Messages between tabs of the same origin; a no-op where BroadcastChannel is missing. */
export function openTabChannel(name: string, onMessage: (message: TabMessage) => void): TabChannel {
  if (typeof BroadcastChannel === 'undefined') {
    return { post: () => {}, close: () => {} }
  }
  const channel = new BroadcastChannel(name)
  channel.onmessage = (event: MessageEvent<TabMessage>) => onMessage(event.data)
  return {
    post: (message: TabMessage) => channel.postMessage(message),
    close: () => channel.close(),
  }
}
