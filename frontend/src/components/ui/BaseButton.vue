<script setup lang="ts">
withDefaults(
  defineProps<{
    type?: 'button' | 'submit'
    variant?: 'primary' | 'secondary' | 'danger'
    loading?: boolean
    disabled?: boolean
  }>(),
  { type: 'button', variant: 'primary', loading: false, disabled: false },
)

const variants = {
  primary: 'bg-indigo-600 text-white hover:bg-indigo-700',
  secondary: 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50',
  danger: 'bg-red-600 text-white hover:bg-red-700',
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :class="[
      'inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium shadow-sm',
      'disabled:cursor-not-allowed disabled:opacity-60',
      variants[variant],
    ]"
  >
    <span
      v-if="loading"
      class="mr-2 size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
    <slot />
  </button>
</template>
