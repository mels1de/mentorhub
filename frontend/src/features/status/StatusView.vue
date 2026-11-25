<script setup lang="ts">
import { computed } from 'vue'

import { useReadiness } from './useReadiness'

const { data, isPending, isError, dataUpdatedAt, errorUpdatedAt } = useReadiness()

type Overall = 'checking' | 'up' | 'degraded' | 'down'

const overall = computed<Overall>(() => {
  // An error wins over stale data: the last good report must not hide that the API is gone.
  if (isError.value) return 'down'
  if (isPending.value) return 'checking'
  return data.value?.status === 'pass' ? 'up' : 'degraded'
})

const banner: Record<Overall, { text: string; classes: string }> = {
  checking: { text: 'Checking…', classes: 'bg-slate-100 text-slate-700' },
  up: { text: 'All systems operational', classes: 'bg-emerald-100 text-emerald-800' },
  degraded: {
    text: 'Degraded: some dependencies are failing',
    classes: 'bg-amber-100 text-amber-800',
  },
  down: { text: 'API unreachable', classes: 'bg-red-100 text-red-800' },
}

const checkedAt = computed(() => {
  const at = Math.max(dataUpdatedAt.value, errorUpdatedAt.value)
  return at ? new Date(at).toLocaleTimeString() : null
})
</script>

<template>
  <main class="mx-auto max-w-xl p-6">
    <h1 class="mb-4 text-2xl font-semibold">MentorHub status</h1>

    <p
      role="status"
      data-testid="overall"
      :data-state="overall"
      :class="['rounded-lg px-4 py-3 font-medium', banner[overall].classes]"
    >
      {{ banner[overall].text }}
    </p>

    <ul
      v-if="data && !isError"
      class="mt-4 divide-y divide-slate-200 rounded-lg bg-white shadow-sm"
    >
      <li
        v-for="(result, name) in data.checks"
        :key="name"
        :data-testid="`check-${name}`"
        class="flex justify-between px-4 py-2"
      >
        <span class="capitalize">{{ name }}</span>
        <span :class="result === 'pass' ? 'text-emerald-700' : 'text-red-700'">{{ result }}</span>
      </li>
    </ul>

    <p v-if="checkedAt" class="mt-3 text-sm text-slate-500">
      Last checked at {{ checkedAt }} · refreshes every 10 s
    </p>
  </main>
</template>
