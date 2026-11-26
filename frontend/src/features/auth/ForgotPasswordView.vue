<script setup lang="ts">
import { useForm } from 'vee-validate'
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import { requestPasswordReset } from '@/api/auth'
import { toProblem } from '@/api/problem'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import AuthCard from '@/components/ui/AuthCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import TextField from '@/components/ui/TextField.vue'
import { zodSchema } from '@/lib/zodSchema'

import { forgotPasswordSchema } from './schemas'

const sent = ref(false)
const serverError = ref<string | null>(null)

const { handleSubmit, defineField, errors, isSubmitting } = useForm({
  validationSchema: zodSchema(forgotPasswordSchema),
  initialValues: { email: '' },
})
const [email] = defineField('email')

const submit = handleSubmit(async (values) => {
  serverError.value = null
  try {
    await requestPasswordReset(values.email)
    sent.value = true
  } catch (error) {
    serverError.value = toProblem(error).detail
  }
})
</script>

<template>
  <AuthCard title="Reset your password">
    <!-- Same message whether or not the email is registered: the API doesn't tell either. -->
    <AlertMessage v-if="sent" tone="success">
      If an account exists for that email, a reset link is on its way. It is valid for 30 minutes.
    </AlertMessage>
    <form v-else class="space-y-4" novalidate @submit="submit">
      <AlertMessage v-if="serverError">{{ serverError }}</AlertMessage>
      <TextField
        v-model="email"
        label="Email"
        type="email"
        autocomplete="email"
        :error="errors.email"
      />
      <BaseButton type="submit" class="w-full" :loading="isSubmitting">Send reset link</BaseButton>
    </form>
    <RouterLink
      :to="{ name: 'login' }"
      class="block text-center text-sm text-indigo-700 hover:underline"
    >
      Back to login
    </RouterLink>
  </AuthCard>
</template>
