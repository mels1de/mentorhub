<script setup lang="ts">
import { watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/layout/AppHeader.vue'
import InactivityGuard from '@/features/auth/InactivityGuard.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// Logged out elsewhere (another tab, expired session): leave pages that need a login.
watch(
  () => auth.isAuthenticated,
  (isAuthenticated) => {
    if (!isAuthenticated && route.meta.requiresAuth) {
      void router.replace({ name: 'login', query: { redirect: route.fullPath } })
    }
  },
)
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900">
    <AppHeader />
    <RouterView />
    <InactivityGuard v-if="auth.isAuthenticated" />
  </div>
</template>
