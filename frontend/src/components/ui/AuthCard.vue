<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
  <main class="flex min-h-[80vh] items-center justify-center px-4">
    <section
      class="w-full max-w-md space-y-6 rounded-xl bg-white p-8 shadow-sm ring-1 ring-slate-200"
    >
      <h1 class="text-2xl font-semibold">{{ title }}</h1>
      <slot />
    </section>
  </main>
</template>
