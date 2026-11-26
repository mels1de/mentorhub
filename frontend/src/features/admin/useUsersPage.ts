import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'

import { fetchUsers } from '@/api/auth'

export const USERS_PAGE_SIZE = 20

export function useUsersPage(page: Ref<number>) {
  return useQuery({
    queryKey: ['users', page],
    queryFn: () => fetchUsers(page.value, USERS_PAGE_SIZE),
    // Keep showing the current page while the next one loads, instead of a blank table.
    placeholderData: keepPreviousData,
  })
}
