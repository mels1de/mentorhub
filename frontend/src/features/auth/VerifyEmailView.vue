<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { verifyEmail } from '@/api/auth'
import { toProblem } from '@/api/problem'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import AuthCard from '@/components/ui/AuthCard.vue'
import { useAuthStore } from '@/stores/auth'

import { takeTokenFromHash } from './linkToken'

const auth = useAuthStore()
const state = ref<'verifying' | 'verified' | 'failed'>('verifying')
const error = ref('This page needs the link from the confirmation email.')

onMounted(async () => {
  const token = takeTokenFromHash()
  if (!token) {
    state.value = 'failed'
    return
  }
  try {
    await verifyEmail(token)
    state.value = 'verified'
    if (auth.isAuthenticated) await auth.loadUser()
  } catch (e) {
    error.value = toProblem(e).detail
    state.value = 'failed'
  }
})
</script>

<template>
  <AuthCard title="Email confirmation">
    <p v-if="state === 'verifying'" role="status" class="text-slate-600">Confirming…</p>
    <AlertMessage v-else-if="state === 'verified'" tone="success">
      Your email is confirmed.
    </AlertMessage>
    <AlertMessage v-else>{{ error }}</AlertMessage>
    <RouterLink
      v-if="state !== 'verifying'"
      :to="auth.isAuthenticated ? { name: 'account' } : { name: 'login' }"
      class="block text-center text-sm text-indigo-700 hover:underline"
    >
      {{ auth.isAuthenticated ? 'Go to your account' : 'Go to login' }}
    </RouterLink>
  </AuthCard>
</template>
