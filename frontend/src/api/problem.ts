import { isAxiosError } from 'axios'

export interface FieldError {
  loc: (string | number)[]
  msg: string
}

export interface Problem {
  status: number
  code: string | null
  detail: string
  errors: FieldError[]
  retryAfter: number | null
  attemptsLeft: number | null
}

const FALLBACK = 'Something went wrong. Please try again.'

/** Normalise any thrown value into the RFC 9457 body the API sends (or a network error). */
export function toProblem(error: unknown): Problem {
  if (!isAxiosError(error)) {
    return {
      status: 0,
      code: null,
      detail: FALLBACK,
      errors: [],
      retryAfter: null,
      attemptsLeft: null,
    }
  }
  if (!error.response) {
    return {
      status: 0,
      code: 'network_error',
      detail: 'Cannot reach the server. Check your connection.',
      errors: [],
      retryAfter: null,
      attemptsLeft: null,
    }
  }
  const body = (error.response.data ?? {}) as Record<string, unknown>
  const retryAfter = Number(error.response.headers['retry-after'])
  return {
    status: error.response.status,
    code: typeof body.code === 'string' ? body.code : null,
    detail: typeof body.detail === 'string' ? body.detail : FALLBACK,
    errors: Array.isArray(body.errors) ? (body.errors as FieldError[]) : [],
    retryAfter: Number.isFinite(retryAfter) ? retryAfter : null,
    attemptsLeft: typeof body.attempts_left === 'number' ? body.attempts_left : null,
  }
}

/** Map 422 field errors onto form field names (the last `loc` segment). */
export function fieldErrors(problem: Problem): Record<string, string> {
  const result: Record<string, string> = {}
  for (const error of problem.errors) {
    const field = error.loc[error.loc.length - 1]
    if (typeof field === 'string' && !(field in result)) result[field] = error.msg
  }
  return result
}
