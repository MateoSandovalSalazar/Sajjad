import { api } from './client'
import type { User } from '../types'

export const usersApi = {
  update: (data: { full_name?: string; company?: string }) =>
    api.patch<User>('/users/me', data),

  changePassword: (current_password: string, new_password: string) =>
    api.post<{ message: string }>('/users/me/password', {
      current_password,
      new_password,
    }),
}
