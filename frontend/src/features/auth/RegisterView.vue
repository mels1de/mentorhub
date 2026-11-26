<script setup lang="ts">
import { useForm } from 'vee-validate'
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { register } from '@/api/auth'
import { fieldErrors, toProblem } from '@/api/problem'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import AuthCard from '@/components/ui/AuthCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import TextField from '@/components/ui/TextField.vue'
import { zodSchema } from '@/lib/zodSchema'
import { useAuthStore } from '@/stores/auth'

import { MIN_PASSWORD, registerSchema } from './schemas'

const auth = useAuthStore()
const router = useRouter()
const serverError = ref<string | null>(null)

const { handleSubmit, defineField, errors, isSubmitting, setErrors } = useForm({
  validationSchema: zodSchema(registerSchema),
  initialValues: { email: '', password: '', confirm: '', role: 'mentee' as const },
})
const [email] = defineField('email')
const [password] = defineField('password')
const [confirm] = defineField('confirm')
const [role] = defineField('role')

const submit = handleSubmit(async (values) => {
  serverError.value = null
  try {
    await register({ email: values.email, password: values.password, role: values.role })
    // Log straight in: a new account has 2FA off, so this never needs a code.
    await auth.login(values.email, values.password)
    await router.replace({ name: 'home', query: { welcome: '1' } })
  } catch (error) {
    const problem = toProblem(error)
    if (problem.code === 'email_taken') setErrors({ email: problem.detail })
    else if (problem.errors.length) setErrors(fieldErrors(problem))
    else serverError.value = problem.detail
  }
})
</script>

<template>
  <AuthCard title="Create an account">
    <form class="space-y-4" novalidate @submit="submit">
      <AlertMessage v-if="serverError">{{ serverError }}</AlertMessage>
      <fieldset class="space-y-1">
        <legend class="text-sm font-medium text-slate-700">I want to</legend>
        <div class="grid grid-cols-2 gap-2">
          <label
            v-for="option in [
              { value: 'mentee', label: 'Find a mentor' },
              { value: 'mentor', label: 'Mentor others' },
            ]"
            :key="option.value"
            :class="[
              'cursor-pointer rounded-md px-3 py-2 text-center text-sm ring-1',
              role === option.value
                ? 'bg-indigo-50 ring-indigo-500 text-indigo-800'
                : 'ring-slate-300 hover:bg-slate-50',
            ]"
          >
            <input v-model="role" type="radio" name="role" :value="option.value" class="sr-only" />
            {{ option.label }}
          </label>
        </div>
      </fieldset>
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
        autocomplete="new-password"
        :hint="`At least ${MIN_PASSWORD} characters.`"
        :error="errors.password"
      />
      <TextField
        v-model="confirm"
        label="Repeat password"
        type="password"
        autocomplete="new-password"
        :error="errors.confirm"
      />
      <BaseButton type="submit" class="w-full" :loading="isSubmitting">Create account</BaseButton>
      <p class="text-center text-sm">
        Already registered?
        <RouterLink :to="{ name: 'login' }" class="text-indigo-700 hover:underline"
          >Log in</RouterLink
        >
      </p>
    </form>
  </AuthCard>
</template>
