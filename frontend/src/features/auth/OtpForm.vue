<script setup lang="ts">
import { useForm } from 'vee-validate'
import { ref } from 'vue'

import { resendOtp, type OtpChallenge } from '@/api/auth'
import { toProblem } from '@/api/problem'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import TextField from '@/components/ui/TextField.vue'
import { zodSchema } from '@/lib/zodSchema'
import { useAuthStore } from '@/stores/auth'

import { otpSchema } from './schemas'

const props = defineProps<{ challenge: OtpChallenge }>()
const emit = defineEmits<{ done: []; cancel: [] }>()

const auth = useAuthStore()
const serverError = ref<string | null>(null)
const notice = ref<string | null>(null)
const locked = ref(false)
const resending = ref(false)

const { handleSubmit, defineField, errors, isSubmitting } = useForm({
  validationSchema: zodSchema(otpSchema),
  initialValues: { code: '' },
})
const [code] = defineField('code')

const submit = handleSubmit(async (values) => {
  serverError.value = null
  notice.value = null
  try {
    await auth.completeOtp(props.challenge.challenge_id, values.code)
    emit('done')
  } catch (error) {
    const problem = toProblem(error)
    locked.value = problem.code === 'otp_locked'
    serverError.value =
      problem.attemptsLeft !== null
        ? `${problem.detail} Attempts left: ${problem.attemptsLeft}.`
        : problem.detail
  }
})

async function resend(): Promise<void> {
  resending.value = true
  serverError.value = null
  try {
    await resendOtp(props.challenge.challenge_id)
    notice.value = 'A new code is on its way.'
  } catch (error) {
    serverError.value = toProblem(error).detail
  } finally {
    resending.value = false
  }
}
</script>

<template>
  <form class="space-y-4" novalidate @submit="submit">
    <p class="text-sm text-slate-600">
      We sent a 6-digit code to your email. It is valid for
      {{ Math.round(challenge.expires_in / 60) }} minutes.
    </p>
    <AlertMessage v-if="serverError">{{ serverError }}</AlertMessage>
    <AlertMessage v-if="notice" tone="success">{{ notice }}</AlertMessage>
    <TextField
      v-model="code"
      label="Login code"
      autocomplete="one-time-code"
      inputmode="numeric"
      :error="errors.code"
    />
    <div class="flex items-center justify-between gap-2">
      <BaseButton type="submit" :loading="isSubmitting" :disabled="locked">Verify</BaseButton>
      <div class="flex gap-2">
        <BaseButton variant="secondary" :loading="resending" :disabled="locked" @click="resend">
          Resend code
        </BaseButton>
        <BaseButton variant="secondary" @click="emit('cancel')">Back</BaseButton>
      </div>
    </div>
  </form>
</template>
