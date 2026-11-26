<script setup lang="ts">
import { useId } from 'vue'

defineProps<{
  label: string
  error?: string
  type?: 'text' | 'email' | 'password'
  autocomplete?: string
  inputmode?: 'text' | 'numeric' | 'email'
  hint?: string
}>()

const model = defineModel<string>({ default: '' })
const id = useId()
</script>

<template>
  <div class="space-y-1">
    <label :for="id" class="block text-sm font-medium text-slate-700">{{ label }}</label>
    <input
      :id="id"
      v-model="model"
      :type="type ?? 'text'"
      :autocomplete="autocomplete"
      :inputmode="inputmode"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? `${id}-error` : hint ? `${id}-hint` : undefined"
      :class="[
        'block w-full rounded-md border bg-white px-3 py-2 shadow-sm focus:outline-none focus:ring-2',
        error
          ? 'border-red-400 focus:ring-red-200'
          : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-200',
      ]"
    />
    <p v-if="error" :id="`${id}-error`" class="text-sm text-red-700">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-hint`" class="text-sm text-slate-500">{{ hint }}</p>
  </div>
</template>
