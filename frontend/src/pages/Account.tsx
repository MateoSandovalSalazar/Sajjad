import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { User as UserIcon, Check, Crown, Sparkles } from 'lucide-react'
import { usersApi } from '../api/users'
import { billingApi } from '../api/billing'
import { useAuthStore } from '../store/auth'
import { toast } from '../store/toast'
import { Spinner } from '../components/ui/Spinner'
import type { PlanInfo } from '../types'

const PLAN_LABELS: Record<string, string> = {
  free:         'Free',
  starter:      'Starter',
  professional: 'Professional',
  agency:       'Agency',
}

function ProfileSection() {
  const { user, updateUser } = useAuthStore()
  const [fullName, setFullName] = useState('')
  const [company, setCompany]   = useState('')

  useEffect(() => {
    setFullName(user?.full_name ?? '')
    setCompany(user?.company ?? '')
  }, [user])

  const dirty =
    fullName !== (user?.full_name ?? '') ||
    company !== (user?.company ?? '')

  const save = useMutation({
    mutationFn: () =>
      usersApi.update({ full_name: fullName, company }).then(r => r.data),
    onSuccess: (data) => {
      updateUser(data)
      toast.success('Perfil actualizado.')
    },
    onError: () => toast.error('No se pudo actualizar el perfil.'),
  })

  return (
    <div className="card p-6">
      <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
        <UserIcon className="h-5 w-5 text-obsidian-700" />
        Perfil
      </h2>

      <div className="space-y-4 max-w-md">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Nombre completo
          </label>
          <input value={fullName} onChange={e => setFullName(e.target.value)}
            className="input" placeholder="Tu nombre" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Empresa
          </label>
          <input value={company} onChange={e => setCompany(e.target.value)}
            className="input" placeholder="Tu empresa" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Correo electrónico
          </label>
          <input value={user?.email ?? ''} disabled
            className="input bg-gray-50 text-gray-400 cursor-not-allowed" />
          <p className="text-xs text-gray-400 mt-1">
            El correo no se puede cambiar.
          </p>
        </div>

        <button onClick={() => save.mutate()}
          disabled={!dirty || save.isPending}
          className="btn-primary flex items-center gap-2">
          {save.isPending ? <Spinner size="sm" /> : <Check className="h-4 w-4" />}
          Guardar cambios
        </button>
      </div>
    </div>
  )
}

function PlanCard({ plan, current }: { plan: PlanInfo; current: boolean }) {
  const label = PLAN_LABELS[plan.name] ?? plan.name
  const featured = plan.name === 'professional'

  const interval = plan.scan_interval_days === 1
    ? 'Escaneos diarios'
    : plan.scan_interval_days
      ? `Escaneos cada ${plan.scan_interval_days} días`
      : 'Escaneos manuales'

  return (
    <div className={`rounded-2xl p-6 border-2 relative flex flex-col ${
      current
        ? 'border-gold-500 bg-gold-50/40'
        : featured
          ? 'border-obsidian-700 bg-white'
          : 'border-gray-100 bg-white'
    }`}>
      {current && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gold-500
          text-obsidian-900 text-xs font-bold px-3 py-0.5 rounded-full
          uppercase tracking-widest">
          Tu plan
        </span>
      )}

      <h3 className="font-black text-lg text-obsidian-900">{label}</h3>
      <div className="my-3">
        <span className="text-4xl font-black text-obsidian-900">
          ${plan.price_usd}
        </span>
        <span className="text-sm text-gray-400 ml-1">USD/mes</span>
      </div>

      <ul className="space-y-2 mb-6 flex-1">
        <li className="flex items-center gap-2 text-sm text-gray-600">
          <Check className="h-4 w-4 text-green-500 shrink-0" />
          {plan.max_domains} dominio{plan.max_domains > 1 ? 's' : ''}
        </li>
        <li className="flex items-center gap-2 text-sm text-gray-600">
          <Check className="h-4 w-4 text-green-500 shrink-0" />
          {interval}
        </li>
        <li className="flex items-center gap-2 text-sm text-gray-600">
          <Check className="h-4 w-4 text-green-500 shrink-0" />
          {plan.max_scans_per_month} escaneos/mes
        </li>
        {plan.can_download_pdf && (
          <li className="flex items-center gap-2 text-sm text-gray-600">
            <Check className="h-4 w-4 text-green-500 shrink-0" />
            Reporte PDF
          </li>
        )}
        {plan.white_label && (
          <li className="flex items-center gap-2 text-sm text-gray-600">
            <Check className="h-4 w-4 text-green-500 shrink-0" />
            Reportes white-label
          </li>
        )}
      </ul>

      {current ? (
        <button disabled
          className="btn-secondary w-full opacity-60 cursor-default">
          Plan actual
        </button>
      ) : (
        <button
          onClick={() => toast.info(
            'El pago en línea estará disponible muy pronto. ' +
            'Escríbenos para activar tu plan.',
          )}
          className="btn-primary w-full flex items-center justify-center gap-2">
          <Sparkles className="h-4 w-4" />
          Mejorar a {label}
        </button>
      )}
    </div>
  )
}

function PlansSection() {
  const { data: plans, isLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: () => billingApi.plans().then(r => r.data),
    staleTime: 60 * 60_000,
  })

  // 404 = sin suscripción = plan free. No reintentar.
  const { data: sub } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => billingApi.subscription().then(r => r.data),
    retry: false,
  })

  const currentPlan = sub?.plan ?? 'free'

  return (
    <div className="card p-6">
      <h2 className="font-bold text-gray-900 mb-1 flex items-center gap-2">
        <Crown className="h-5 w-5 text-gold-500" />
        Tu plan
      </h2>
      <p className="text-sm text-gray-500 mb-5">
        Plan actual: <strong>{PLAN_LABELS[currentPlan] ?? currentPlan}</strong>
        {sub && (
          <> · {sub.scans_this_month} escaneos este mes</>
        )}
      </p>

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans?.map(p => (
            <PlanCard key={p.name} plan={p}
              current={p.name === currentPlan} />
          ))}
        </div>
      )}
    </div>
  )
}

export function Account() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-black text-gray-900">Mi cuenta</h1>
        <p className="text-gray-500 mt-1">
          Administra tu perfil y tu plan de suscripción.
        </p>
      </div>

      <div className="space-y-6">
        <ProfileSection />
        <PlansSection />
      </div>
    </div>
  )
}
