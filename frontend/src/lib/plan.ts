// Espejo de backend/app/core/limits.py — capacidades por plan.
// Si cambias los límites en el backend, actualiza esto también.

export interface PlanCaps {
  canSeeFindings: boolean
  canDownloadPdf: boolean
  maxDomains: number
  maxScansPerMonth: number
}

export const PLAN_CAPS: Record<string, PlanCaps> = {
  free:         { canSeeFindings: false, canDownloadPdf: false, maxDomains: 1,  maxScansPerMonth: 1 },
  starter:      { canSeeFindings: true,  canDownloadPdf: true,  maxDomains: 1,  maxScansPerMonth: 4 },
  professional: { canSeeFindings: true,  canDownloadPdf: true,  maxDomains: 3,  maxScansPerMonth: 30 },
  agency:       { canSeeFindings: true,  canDownloadPdf: true,  maxDomains: 10, maxScansPerMonth: 300 },
}

export function planCaps(plan: string): PlanCaps {
  return PLAN_CAPS[plan] ?? PLAN_CAPS.free
}
