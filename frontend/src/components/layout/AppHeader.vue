<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { RouterLink, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const queryClient = useQueryClient()

async function logout(): Promise<void> {
  await auth.logout()
  // Cached responses belong to the previous user.
  queryClient.clear()
  await router.replace({ name: 'login' })
}
</script>

<template>
  <header class="border-b border-slate-200 bg-white">
    <nav class="mx-auto flex max-w-5xl items-center gap-6 px-6 py-3 text-sm">
      <RouterLink :to="{ name: 'home' }" class="font-semibold text-indigo-700"
        >MentorHub</RouterLink
      >
      <template v-if="auth.isAuthenticated">
        <RouterLink :to="{ name: 'account' }" class="hover:underline">Account</RouterLink>
        <RouterLink
          v-if="auth.hasRole('admin')"
          :to="{ name: 'admin-users' }"
          class="hover:underline"
        >
          Users
        </RouterLink>
        <span class="ml-auto text-slate-500">{{ auth.user?.email }}</span>
        <button type="button" class="text-slate-700 hover:underline" @click="logout">
          Log out
        </button>
      </template>
      <template v-else>
        <RouterLink :to="{ name: 'login' }" class="ml-auto hover:underline">Log in</RouterLink>
        <RouterLink :to="{ name: 'register' }" class="hover:underline">Sign up</RouterLink>
      </template>
    </nav>
  </header>
</template>
