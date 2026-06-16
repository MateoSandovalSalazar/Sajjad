import { useQuery } from '@tanstack/react-query'
import { billingApi } from '../api/billing'
import { planCaps } from '../lib/plan'

// Plan actual del usuario + sus capacidades. Si no hay suscripción
// (404) se asume "free".
export function usePlan() {
  const { data: sub, isLoading } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => billingApi.subscription().then(r => r.data),
    retry: false,
    staleTime: 5 * 60_000,
  })

  const plan = sub?.plan ?? 'free'
  return { plan, caps: planCaps(plan), subscription: sub, isLoading }
}
