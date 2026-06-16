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
}
