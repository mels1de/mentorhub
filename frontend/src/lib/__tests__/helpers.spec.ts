import { AxiosError, type AxiosResponse } from 'axios'
import { describe, expect, it } from 'vitest'
import { z } from 'zod'

import { fieldErrors, toProblem } from '@/api/problem'
import { safeRedirect, takeTokenFromHash } from '@/features/auth/linkToken'

import { zodSchema } from '../zodSchema'

describe('zodSchema', () => {
  const schema = zodSchema(
    z.object({ email: z.email('bad email'), age: z.number().min(18, 'too young') }),
  )

  it('returns the parsed value when valid', async () => {
    await expect(schema.parse({ email: 'a@b.co', age: 20 })).resolves.toEqual({
      value: { email: 'a@b.co', age: 20 },
      errors: [],
    })
  })

  it('maps issues to field paths', async () => {
    const result = await schema.parse({ email: 'x', age: 3 })

    expect(result.value).toBeUndefined()
    expect(result.errors).toEqual([
      { path: 'email', errors: ['bad email'] },
      { path: 'age', errors: ['too young'] },
    ])
  })
})

describe('toProblem', () => {
  it('reads RFC 9457 bodies and Retry-After', () => {
    const response = {
      status: 429,
      data: { code: 'rate_limited', detail: 'Slow down.' },
      headers: { 'retry-after': '30' },
    } as unknown as AxiosResponse
    const problem = toProblem(new AxiosError('x', '429', undefined, undefined, response))

    expect(problem).toMatchObject({
      status: 429,
      code: 'rate_limited',
      detail: 'Slow down.',
      retryAfter: 30,
    })
  })

  it('reports a network error when there is no response', () => {
    expect(toProblem(new AxiosError('Network Error')).code).toBe('network_error')
  })

  it('maps 422 field errors by their last loc segment', () => {
    const problem = toProblem(
      new AxiosError('x', '422', undefined, undefined, {
        status: 422,
        data: { errors: [{ loc: ['body', 'email'], msg: 'invalid' }] },
        headers: {},
      } as unknown as AxiosResponse),
    )

    expect(fieldErrors(problem)).toEqual({ email: 'invalid' })
  })
})

describe('link helpers', () => {
  it('takes the token from the fragment and removes it from the URL', () => {
    window.history.replaceState(null, '', '/reset-password#token=abc-123')

    expect(takeTokenFromHash()).toBe('abc-123')
    expect(window.location.hash).toBe('')
    expect(takeTokenFromHash()).toBeNull()
  })

  it.each([
    ['/account', '/account'],
    ['//evil.example', null],
    ['https://evil.example', null],
    [undefined, null],
  ])('safeRedirect(%s) is %s', (input, expected) => {
    expect(safeRedirect(input)).toBe(expected)
  })
})
