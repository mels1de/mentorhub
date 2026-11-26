<script setup lang="ts">
import { ref } from 'vue'

import { toProblem } from '@/api/problem'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

import { useUsersPage } from './useUsersPage'

const page = ref(1)
const { data, isPending, isError, error, isPlaceholderData } = useUsersPage(page)
</script>

<template>
  <main class="mx-auto max-w-4xl space-y-4 p-6">
    <h1 class="text-2xl font-semibold">Users</h1>

    <p v-if="isPending" role="status" class="text-slate-600">Loading…</p>
    <AlertMessage v-else-if="isError">{{ toProblem(error).detail }}</AlertMessage>
    <p v-else-if="data && data.total === 0" class="text-slate-600">No users yet.</p>

    <template v-else-if="data">
      <table
        :class="[
          'w-full overflow-hidden rounded-lg bg-white text-sm shadow-sm ring-1 ring-slate-200',
          isPlaceholderData && 'opacity-60',
        ]"
      >
        <thead class="bg-slate-50 text-left text-slate-500">
          <tr>
            <th class="px-4 py-2">Email</th>
            <th class="px-4 py-2">Role</th>
            <th class="px-4 py-2">Verified</th>
            <th class="px-4 py-2">2FA</th>
            <th class="px-4 py-2">Joined</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="user in data.items" :key="user.id" data-testid="user-row">
            <td class="px-4 py-2">{{ user.email }}</td>
            <td class="px-4 py-2 capitalize">{{ user.role }}</td>
            <td class="px-4 py-2">{{ user.is_email_verified ? 'confirmed' : '—' }}</td>
            <td class="px-4 py-2">{{ user.is_2fa_enabled ? 'on' : 'off' }}</td>
            <td class="px-4 py-2">{{ new Date(user.created_at).toLocaleDateString() }}</td>
          </tr>
        </tbody>
      </table>
      <nav class="flex items-center justify-between text-sm" aria-label="Pagination">
        <span>Page {{ data.page }} of {{ Math.max(data.pages, 1) }} · {{ data.total }} users</span>
        <div class="flex gap-2">
          <BaseButton variant="secondary" :disabled="page <= 1" @click="page--"
            >Previous</BaseButton
          >
          <BaseButton variant="secondary" :disabled="page >= data.pages" @click="page++"
            >Next</BaseButton
          >
        </div>
      </nav>
    </template>
  </main>
</template>
