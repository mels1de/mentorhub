<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'

import BaseButton from '@/components/ui/BaseButton.vue'
import { useAuthStore } from '@/stores/auth'

import { useInactivityTimer } from './useInactivityTimer'

const auth = useAuthStore()
const router = useRouter()
const queryClient = useQueryClient()

const { showWarning, secondsLeft, stayActive } = useInactivityTimer({
  onTimeout: async () => {
    await auth.logout().catch(() => auth.clear())
    queryClient.clear()
    await router.replace({ name: 'login', query: { reason: 'inactivity' } })
  },
})
</script>

<template>
  <div
    v-if="showWarning"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
  >
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="inactivity-title"
      class="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow-lg"
    >
      <h2 id="inactivity-title" class="text-lg font-semibold">Are you still there?</h2>
      <p class="text-slate-600" data-testid="inactivity-countdown">
        For your security you will be logged out in
        {{ Math.floor(secondsLeft / 60) }}:{{ String(secondsLeft % 60).padStart(2, '0') }}.
      </p>
      <BaseButton class="w-full" @click="stayActive">Stay logged in</BaseButton>
    </div>
  </div>
</template>
