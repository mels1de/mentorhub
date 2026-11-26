<script setup lang="ts">
import { useForm } from 'vee-validate'
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import type { OtpChallenge } from '@/api/auth'
import { toProblem } from '@/api/problem'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import AuthCard from '@/components/ui/AuthCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import TextField from '@/components/ui/TextField.vue'
import { zodSchema } from '@/lib/zodSchema'
import { useAuthStore } from '@/stores/auth'

import { safeRedirect } from './linkToken'
import OtpForm from './OtpForm.vue'
import { loginSchema } from './schemas'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const challenge = ref<OtpChallenge | null>(null)
const serverError = ref<string | null>(null)

const notices: Record<string, string> = {
  expired: 'Your session has expired. Please log in again.',
  inactivity: 'You were logged out after a period of inactivity.',
  'password-reset': 'Your password was changed. Log in with the new one.',
}
const notice = computed(() => notices[String(route.query.reason)] ?? null)

const { handleSubmit, defineField, errors, isSubmitting } = useForm({
  validationSchema: zodSchema(loginSchema),
  initialValues: { email: '', password: '' },
})
const [email] = defineField('email')
const [password] = defineField('password')

const submit = handleSubmit(async (values) => {
  serverError.value = null
  try {
    const result = await auth.login(values.email, values.password)
    if (result.status === 'otp_required') challenge.value = result
    else await goToApp()
  } catch (error) {
    serverError.value = toProblem(error).detail
  }
})

async function goToApp(): Promise<void> {
  await router.replace(safeRedirect(route.query.redirect) ?? { name: 'home' })
}
</script>

<template>
  <AuthCard :title="challenge ? 'Enter your login code' : 'Log in'">
    <OtpForm v-if="challenge" :challenge="challenge" @done="goToApp" @cancel="challenge = null" />

    <form v-else class="space-y-4" novalidate @submit="submit">
      <AlertMessage v-if="notice" tone="info">{{ notice }}</AlertMessage>
      <AlertMessage v-if="serverError">{{ serverError }}</AlertMessage>
      <TextField
        v-model="email"
        label="Email"
        type="email"
        autocomplete="email"
        :error="errors.email"
      />
      <TextField
        v-model="password"
        label="Password"
        type="password"
        autocomplete="current-password"
        :error="errors.password"
      />
      <BaseButton type="submit" class="w-full" :loading="isSubmitting">Log in</BaseButton>
      <div class="flex justify-between text-sm">
        <RouterLink :to="{ name: 'forgot-password' }" class="text-indigo-700 hover:underline">
          Forgot password?
        </RouterLink>
        <RouterLink :to="{ name: 'register' }" class="text-indigo-700 hover:underline">
          Create an account
        </RouterLink>
      </div>
    </form>
  </AuthCard>
</template>
