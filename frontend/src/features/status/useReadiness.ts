import { useQuery } from '@tanstack/vue-query'

import { fetchReadiness } from '@/api/health'

export const READINESS_POLL_MS = 10_000

export function useReadiness() {
  return useQuery({
    queryKey: ['health', 'ready'],
    queryFn: ({ signal }) => fetchReadiness(signal),
    refetchInterval: READINESS_POLL_MS,
    // The next poll is the retry; backing off would hide an outage for longer.
    retry: false,
  })
}
