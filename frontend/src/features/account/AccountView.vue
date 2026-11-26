<script setup lang="ts">
import { useForm } from 'vee-validate'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { resendVerification, setTwoFactor } from '@/api/auth'
import { toProblem } from '@/api/problem'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import TextField from '@/components/ui/TextField.vue'
import { passwordConfirmSchema } from '@/features/auth/schemas'
import { zodSchema } from '@/lib/zodSchema'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const message = ref<{ tone: 'success' | 'error'; text: string } | null>(null)
const resending = ref(false)
const confirming2fa = ref(false)

const { handleSubmit, defineField, errors, isSubmitting, resetForm } = useForm({
  validationSchema: zodSchema(passwordConfirmSchema),
  initialValues: { password: '' },
})
const [password] = defineField('password')

async function resend(): Promise<void> {
  resending.value = true
  try {
    await resendVerification()
    message.value = { tone: 'success', text: 'A new confirmation link is on its way.' }
  } catch (error) {
    message.value = { tone: 'error', text: toProblem(error).detail }
  } finally {
    resending.value = false
  }
}

const toggle2fa = handleSubmit(async (values) => {
  const enable = !auth.user?.is_2fa_enabled
  try {
    await setTwoFactor(enable, values.password)
    await auth.loadUser()
    confirming2fa.value = false
    resetForm()
    message.value = {
      tone: 'success',
      text: enable
        ? 'Two-factor login is on: next time we will email you a code.'
        : 'Two-factor login is off.',
    }
  } catch (error) {
    message.value = { tone: 'error', text: toProblem(error).detail }
  }
})

async function logoutEverywhere(): Promise<void> {
  await auth.logoutEverywhere()
  await router.replace({ name: 'login' })
}
</script>

<template>
  <main v-if="auth.user" class="mx-auto max-w-2xl space-y-6 p-6">
    <h1 class="text-2xl font-semibold">Your account</h1>
    <AlertMessage v-if="message" :tone="message.tone">{{ message.text }}</AlertMessage>

    <section class="space-y-2 rounded-lg bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h2 class="font-medium">Profile</h2>
      <dl class="grid grid-cols-[8rem_1fr] gap-y-1 text-sm">
        <dt class="text-slate-500">Email</dt>
        <dd>{{ auth.user.email }}</dd>
        <dt class="text-slate-500">Role</dt>
        <dd class="capitalize">{{ auth.user.role }}</dd>
        <dt class="text-slate-500">Email status</dt>
        <dd data-testid="email-status">
          {{ auth.user.is_email_verified ? 'Confirmed' : 'Not confirmed' }}
        </dd>
      </dl>
      <BaseButton
        v-if="!auth.user.is_email_verified"
        variant="secondary"
        :loading="resending"
        @click="resend"
      >
        Resend confirmation link
      </BaseButton>
    </section>

    <section class="space-y-3 rounded-lg bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h2 class="font-medium">Two-factor login</h2>
      <p class="text-sm text-slate-600">
        {{
          auth.user.is_2fa_enabled
            ? 'On: after your password we email you a 6-digit code.'
            : 'Off: add a code sent to your email as a second step when you log in.'
        }}
      </p>
      <p v-if="!auth.user.is_email_verified" class="text-sm text-amber-700">
        Confirm your email first — the codes are sent there.
      </p>
      <BaseButton
        v-else-if="!confirming2fa"
        :variant="auth.user.is_2fa_enabled ? 'secondary' : 'primary'"
        @click="confirming2fa = true"
      >
        {{ auth.user.is_2fa_enabled ? 'Turn off' : 'Turn on' }}
      </BaseButton>
      <form v-else class="space-y-3" novalidate @submit="toggle2fa">
        <TextField
          v-model="password"
          label="Confirm with your password"
          type="password"
          autocomplete="current-password"
          :error="errors.password"
        />
        <div class="flex gap-2">
          <BaseButton type="submit" :loading="isSubmitting">Confirm</BaseButton>
          <BaseButton variant="secondary" @click="confirming2fa = false">Cancel</BaseButton>
        </div>
      </form>
    </section>

    <section class="space-y-3 rounded-lg bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h2 class="font-medium">Sessions</h2>
      <p class="text-sm text-slate-600">Log out on every device and browser, including this one.</p>
      <BaseButton variant="danger" @click="logoutEverywhere">Log out everywhere</BaseButton>
    </section>
  </main>
</template>
