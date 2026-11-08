import { Link } from 'react-router-dom'
import { Clock, Sparkles } from 'lucide-react'
import { usePlan } from '../hooks/usePlan'

/**
 * Aviso del estado de la prueba gratuita, visible en todo el panel.
 *
 * Sólo aparece en los últimos días: mostrarlo los 14 días lo convierte
 * en ruido que el usuario deja de ver justo cuando importa.
 */
const WARN_FROM_DAYS = 5

export function TrialBanner() {
  const { isTrial, trialDaysLeft, billingEnabled } = usePlan()

  if (!isTrial || trialDaysLeft === null) return null
  if (trialDaysLeft > WARN_FROM_DAYS) return null

  const urgent = trialDaysLeft <= 2
  const remaining = trialDaysLeft === 0
    ? 'Tu prueba gratuita termina hoy'
    : `Tu prueba gratuita termina en ${trialDaysLeft} día${
        trialDaysLeft === 1 ? '' : 's'}`

  return (
    <div
      role="status"
      className={`mb-6 flex flex-wrap items-center gap-x-4 gap-y-2
        rounded-xl border px-4 py-3 ${
          urgent
            ? 'border-red-200 bg-red-50'
            : 'border-gold-500/40 bg-gold-50/60'
        }`}
    >
      <Clock className={`h-5 w-5 shrink-0 ${
        urgent ? 'text-red-500' : 'text-gold-600'
      }`} />

      <div className="flex-1 min-w-[16rem]">
        <p className="text-sm font-semibold text-obsidian-900">
          {remaining}.
        </p>
        <p className="text-xs text-gray-600">
          Después pasarás al plan Free: seguirás viendo tu Risk Score,
          pero no los hallazgos detallados ni los reportes PDF.
        </p>
      </div>

      <Link
        to="/account"
        className="btn-primary inline-flex items-center gap-2 text-sm"
      >
        <Sparkles className="h-4 w-4" />
        {billingEnabled ? 'Mejorar mi plan' : 'Ver planes'}
      </Link>
    </div>
  )
}
