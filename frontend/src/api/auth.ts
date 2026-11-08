import { api } from './client'
import type { AuthTokens, User } from '../types'

export const authApi = {
  register: (data: {
    email: string
    password: string
    full_name: string
    company?: string
  }) => api.post<{ id: string; email: string }>('/auth/register', data),

  login: (email: string, password: string) =>
    api.post<AuthTokens>('/auth/login', { email, password }),

  refresh: (refresh_token: string) =>
    api.post<AuthTokens>('/auth/refresh', { refresh_token }),

  me: () => api.get<User>('/users/me'),

  verifyEmail: (token: string) =>
    api.get<{ message: string }>(`/auth/verify-email?token=${token}`),

  // Reenvía el enlace de verificación. 202 siempre, exista o no la
  // cuenta y esté o no verificada.
  resendVerification: (email: string) =>
    api.post<{ message: string }>('/auth/resend-verification', { email }),

  // Responde 202 exista o no el correo: el backend no revela qué
  // direcciones están registradas.
  forgotPassword: (email: string) =>
    api.post<{ message: string }>('/auth/forgot-password', { email }),

  resetPassword: (token: string, new_password: string) =>
    api.post<{ message: string }>('/auth/reset-password', {
      token,
      new_password,
    }),
}
