import type { components } from './schema'
import { http } from './http'

export type Readiness = components['schemas']['ReadyResponse']

export async function fetchReadiness(signal?: AbortSignal): Promise<Readiness> {
  const { data } = await http.get<Readiness>('/health/ready', {
    baseURL: '/',
    signal,
    timeout: 5_000,
    // A 503 still carries the per-check report: it is data, not a failed request.
    validateStatus: (status) => status === 200 || status === 503,
  })
  return data
}
