/**
 * Email links carry the token in the URL fragment (#token=...), which browsers never send
 * to servers. Read it once and remove it, so it doesn't stay in history or get copied.
 */
export function takeTokenFromHash(): string | null {
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token')
  if (token) {
    window.history.replaceState(window.history.state, '', window.location.pathname)
  }
  return token
}

/** Only same-site paths: `?redirect=https://evil.example` must not become an open redirect. */
export function safeRedirect(value: unknown): string | null {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
    ? value
    : null
}
