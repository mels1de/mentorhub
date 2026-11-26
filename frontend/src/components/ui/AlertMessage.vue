<script setup lang="ts">
const props = withDefaults(defineProps<{ tone?: 'error' | 'success' | 'info' }>(), {
  tone: 'error',
})

const tones = {
  error: 'bg-red-50 text-red-800 ring-red-200',
  success: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  info: 'bg-sky-50 text-sky-800 ring-sky-200',
}
</script>

<template>
  <div
    :role="props.tone === 'error' ? 'alert' : 'status'"
    :class="['rounded-md px-4 py-3 text-sm ring-1', tones[props.tone]]"
  >
    <slot />
  </div>
</template>
