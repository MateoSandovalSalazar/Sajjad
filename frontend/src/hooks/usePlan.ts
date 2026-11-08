import { useQuery } from '@tanstack/react-query'
import { billingApi } from '../api/billing'
import type { PlanCapabilities } from '../types'

// Capacidades asumidas mientras carga la suscripción, o si la
// petición falla. Deliberadamente las más restrictivas: si no
// sabemos qué plan tiene el usuario, no le mostramos de más.
const LOCKED: PlanCapabilities = {
  max_domains: 1,
  max_scans_per_month: 1,
  scan_interval_days: null,
  can_download_pdf: false,
  can_see_findings: false,
  white_label: false,
}

/**
 * Plan vigente del usuario y lo que puede hacer con él.
 *
 * Las capacidades vienen calculadas del backend (core/limits.py es la
 * fuente única de verdad); aquí no se replica ninguna regla de negocio.
 */
export function usePlan() {
  const { data: sub, isLoading } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => billingApi.subscription().then(r => r.data),
    retry: false,
    staleTime: 5 * 60_000,
  })

  return {
    plan: sub?.plan ?? 'free',
    planLabel: sub?.plan_label ?? 'Free',
    caps: sub?.capabilities ?? LOCKED,
    isTrial: sub?.is_trial ?? false,
    trialDaysLeft: sub?.trial_days_left ?? null,
    billingEnabled: sub?.billing_enabled ?? false,
    subscription: sub,
    isLoading,
  }
}
