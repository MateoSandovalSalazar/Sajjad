import { api } from './client'
import type { PlanInfo, Subscription } from '../types'

export const billingApi = {
  plans: () => api.get<PlanInfo[]>('/billing/plans'),

  // Devuelve 404 si el usuario aún no tiene suscripción (plan free).
  subscription: () => api.get<Subscription>('/billing/subscription'),
}
