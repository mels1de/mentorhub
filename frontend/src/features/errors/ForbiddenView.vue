<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <main class="mx-auto max-w-xl space-y-3 p-6 text-center">
    <h1 class="text-2xl font-semibold">No access</h1>
    <p class="text-slate-600">Your account doesn't have permission to open this page.</p>
    <RouterLink :to="{ name: 'home' }" class="text-indigo-700 hover:underline">Go home</RouterLink>
  </main>
</template>
