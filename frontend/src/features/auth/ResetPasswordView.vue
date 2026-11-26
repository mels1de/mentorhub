<script setup lang="ts">
import { useForm } from 'vee-validate'
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { confirmPasswordReset } from '@/api/auth'
import { toProblem } from '@/api/problem'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import AuthCard from '@/components/ui/AuthCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import TextField from '@/components/ui/TextField.vue'
import { zodSchema } from '@/lib/zodSchema'
import { useAuthStore } from '@/stores/auth'

import { takeTokenFromHash } from './linkToken'
import { resetPasswordSchema } from './schemas'

const auth = useAuthStore()
const router = useRouter()
const token = takeTokenFromHash()
const serverError = ref<string | null>(null)

const { handleSubmit, defineField, errors, isSubmitting } = useForm({
  validationSchema: zodSchema(resetPasswordSchema),
  initialValues: { password: '', confirm: '' },
})
const [password] = defineField('password')
const [confirm] = defineField('confirm')

const submit = handleSubmit(async (values) => {
  if (!token) return
  serverError.value = null
  try {
    await confirmPasswordReset(token, values.password)
    // The API ended every session, including this tab's, if it had one.
    auth.clear()
    auth.broadcast({ type: 'logout' })
    await router.replace({ name: 'login', query: { reason: 'password-reset' } })
  } catch (error) {
    serverError.value = toProblem(error).detail
  }
})
</script>

<template>
  <AuthCard title="Choose a new password">
    <AlertMessage v-if="!token">
      This page needs the link from the reset email.
      <RouterLink :to="{ name: 'forgot-password' }" class="font-medium underline">
        Request a new one
      </RouterLink>
    </AlertMessage>
    <form v-else class="space-y-4" novalidate @submit="submit">
      <AlertMessage v-if="serverError">{{ serverError }}</AlertMessage>
      <TextField
        v-model="password"
        label="New password"
        type="password"
        autocomplete="new-password"
        :error="errors.password"
      />
      <TextField
        v-model="confirm"
        label="Repeat new password"
        type="password"
        autocomplete="new-password"
        :error="errors.confirm"
      />
      <BaseButton type="submit" class="w-full" :loading="isSubmitting">Change password</BaseButton>
    </form>
  </AuthCard>
</template>
