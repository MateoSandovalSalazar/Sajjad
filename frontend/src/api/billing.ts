import { api } from './client'
import type { CheckoutResponse, PlanInfo, Subscription } from '../types'

export const billingApi = {
  // Planes vendibles (no incluye free ni la prueba gratuita).
  plans: () => api.get<PlanInfo[]>('/billing/plans'),

  // Estado del plan del usuario: plan efectivo, capacidades, días de
  // prueba restantes y si la pasarela de pagos está activa.
  subscription: () => api.get<Subscription>('/billing/subscription'),

  // Crea la preferencia de pago en Mercado Pago y devuelve la URL de
  // checkout. Devuelve 503 BillingDisabled mientras los pagos no
  // estén habilitados en el backend.
  checkout: (plan: string) =>
    api.post<CheckoutResponse>('/billing/checkout', { plan }),

  // Cancela la suscripción activa y baja al plan free. También 503
  // si los pagos están apagados.
  cancel: () => api.post<{ message: string }>('/billing/cancel'),
}
