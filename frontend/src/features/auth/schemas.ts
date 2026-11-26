import { z } from 'zod'

// Mirrors backend/app/modules/auth/schemas.py; the server re-validates everything anyway.
export const MIN_PASSWORD = 8
export const MAX_PASSWORD = 128

const email = z.email('Enter a valid email address.')
const newPassword = z
  .string()
  .min(MIN_PASSWORD, `At least ${MIN_PASSWORD} characters.`)
  .max(MAX_PASSWORD, `At most ${MAX_PASSWORD} characters.`)

export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'Enter your password.'),
})

export const registerSchema = z
  .object({
    email,
    password: newPassword,
    confirm: z.string(),
    role: z.enum(['mentee', 'mentor']),
  })
  .refine((v) => v.password === v.confirm, {
    path: ['confirm'],
    message: 'Passwords do not match.',
  })

export const otpSchema = z.object({
  code: z.string().regex(/^\d{6}$/, 'Enter the 6-digit code from the email.'),
})

export const forgotPasswordSchema = z.object({ email })

export const resetPasswordSchema = z
  .object({ password: newPassword, confirm: z.string() })
  .refine((v) => v.password === v.confirm, {
    path: ['confirm'],
    message: 'Passwords do not match.',
  })

export const passwordConfirmSchema = z.object({
  password: z.string().min(1, 'Enter your password.'),
})
