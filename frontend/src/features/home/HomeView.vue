<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import AlertMessage from '@/components/ui/AlertMessage.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()

const roleText = {
  mentee: 'Find a mentor and book sessions — the catalog arrives in the next release.',
  mentor: 'Set up your mentor profile and availability — coming in the next release.',
  admin: 'Manage users of the platform.',
}
const welcome = computed(() => route.query.welcome === '1')
</script>

<template>
  <main v-if="auth.user" class="mx-auto max-w-3xl space-y-6 p-6">
    <AlertMessage v-if="welcome" tone="success">
      Welcome to MentorHub! We sent a confirmation link to {{ auth.user.email }}.
    </AlertMessage>
    <AlertMessage v-else-if="!auth.user.is_email_verified" tone="info">
      Please confirm your email address.
      <RouterLink :to="{ name: 'account' }" class="font-medium underline"
        >Resend the link</RouterLink
      >
    </AlertMessage>

    <h1 class="text-2xl font-semibold">Hello, {{ auth.user.email }}</h1>
    <p class="text-slate-600" data-testid="role-text">{{ roleText[auth.user.role] }}</p>
    <RouterLink
      v-if="auth.hasRole('admin')"
      :to="{ name: 'admin-users' }"
      class="inline-block text-indigo-700 hover:underline"
    >
      Open user management →
    </RouterLink>
  </main>
</template>
