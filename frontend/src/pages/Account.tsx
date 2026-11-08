import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { User as UserIcon, Check, Crown, Sparkles, Mail } from 'lucide-react'
import { usersApi } from '../api/users'
import { billingApi } from '../api/billing'
import { useAuthStore } from '../store/auth'
import { toast } from '../store/toast'
import { getErrorMessage } from '../lib/errors'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { Spinner } from '../components/ui/Spinner'
import type { PlanInfo } from '../types'

// Canal de contratación mientras la pasarela de pagos no esté activa.
const CONTACT_EMAIL = 'hola@sajjad.app'

function ProfileSection() {
  const { user, updateUser } = useAuthStore()
  // Estado inicial perezoso a partir del usuario; el componente se
  // re-monta (key por id en <Account/>) cuando el usuario carga, así
  // evitamos sincronizar con setState dentro de un efecto.
  const [fullName, setFullName] = useState(() => user?.full_name ?? '')
  const [company, setCompany]   = useState(() => user?.company ?? '')

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

function PlanCard({ plan, current, onSelect, loading, billingEnabled }: {
  plan: PlanInfo
  current: boolean
  onSelect: () => void
  loading: boolean
  billingEnabled: boolean
}) {
  const label = plan.label
  const featured = plan.name === 'professional'
  const caps = plan.capabilities

  const interval = caps.scan_interval_days === 1
    ? 'Escaneos diarios'
    : caps.scan_interval_days
      ? `Escaneos cada ${caps.scan_interval_days} días`
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
          {caps.max_domains} dominio{caps.max_domains > 1 ? 's' : ''}
        </li>
        <li className="flex items-center gap-2 text-sm text-gray-600">
          <Check className="h-4 w-4 text-green-500 shrink-0" />
          {interval}
        </li>
        <li className="flex items-center gap-2 text-sm text-gray-600">
          <Check className="h-4 w-4 text-green-500 shrink-0" />
          {caps.max_scans_per_month} escaneos/mes
        </li>
        {caps.can_download_pdf && (
          <li className="flex items-center gap-2 text-sm text-gray-600">
            <Check className="h-4 w-4 text-green-500 shrink-0" />
            Reporte PDF
          </li>
        )}
        {caps.white_label && (
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
      ) : billingEnabled ? (
        <button
          onClick={onSelect}
          disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2">
          {loading
            ? <Spinner size="sm" />
            : <Sparkles className="h-4 w-4" />}
          Mejorar a {label}
        </button>
      ) : (
        // El pago en línea todavía no está activo: en vez de un botón
        // que falla, se ofrece el canal que sí funciona hoy.
        <a href={`mailto:${CONTACT_EMAIL}?subject=${
          encodeURIComponent(`Quiero contratar el plan ${label}`)
        }`}
          className="btn-secondary w-full flex items-center justify-center gap-2">
          <Mail className="h-4 w-4" />
          Contactar para contratar
        </a>
      )}
    </div>
  )
}

function PlansSection() {
  const qc = useQueryClient()

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
  const billingEnabled = sub?.billing_enabled ?? false
  // Sólo se cancela lo que se paga: un trial expira solo.
  const isPaid = currentPlan !== 'free' && !sub?.is_trial

  // Checkout: pide la URL de Mercado Pago y redirige. Si el pago aún
  // no está configurado en el backend, mostramos un mensaje claro.
  const checkout = useMutation({
    mutationFn: (plan: string) =>
      billingApi.checkout(plan).then(r => r.data),
    onSuccess: (data) => {
      window.location.href = data.checkout_url
    },
    onError: (err) =>
      toast.error(getErrorMessage(
        err,
        'El pago en línea no está disponible por ahora. ' +
        'Escríbenos para activar tu plan.',
      )),
  })

  const cancel = useMutation({
    mutationFn: () => billingApi.cancel().then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscription'] })
      toast.success('Suscripción cancelada. Volviste al plan Free.')
    },
    onError: (err) =>
      toast.error(getErrorMessage(err, 'No se pudo cancelar la suscripción.')),
  })

  const confirmCancel = () => {
    if (window.confirm(
      '¿Seguro que quieres cancelar tu suscripción? ' +
      'Perderás el acceso a los hallazgos detallados y reportes PDF.',
    )) cancel.mutate()
  }

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between gap-4 mb-1 flex-wrap">
        <h2 className="font-bold text-gray-900 flex items-center gap-2">
          <Crown className="h-5 w-5 text-gold-500" />
          Tu plan
        </h2>
        {isPaid && billingEnabled && (
          <button onClick={confirmCancel} disabled={cancel.isPending}
            className="text-sm text-gray-400 hover:text-red-600 transition-colors
              disabled:opacity-50">
            {cancel.isPending ? 'Cancelando…' : 'Cancelar suscripción'}
          </button>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-5">
        Plan actual: <strong>{sub?.plan_label ?? 'Free'}</strong>
        {sub && (
          <> · {sub.scans_this_month} escaneos este mes</>
        )}
      </p>

      {sub?.is_trial && sub.trial_days_left !== null && (
        <div className="mb-5 rounded-xl border border-gold-500/40 bg-gold-50/50
          px-4 py-3">
          <p className="text-sm text-obsidian-900 font-semibold">
            Estás en tu prueba gratuita
            {sub.trial_days_left > 0
              ? ` — te quedan ${sub.trial_days_left} día${
                  sub.trial_days_left === 1 ? '' : 's'}`
              : ' — termina hoy'}
            .
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            Incluye 3 dominios, escaneos diarios, hallazgos detallados
            y reportes PDF. Al terminar, tu cuenta pasa al plan Free
            sin que se te cobre nada.
          </p>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans?.map(p => (
            <PlanCard key={p.name} plan={p}
              current={p.name === currentPlan}
              billingEnabled={billingEnabled}
              loading={checkout.isPending && checkout.variables === p.name}
              onSelect={() => checkout.mutate(p.name)} />
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400 mt-5 flex items-center gap-1.5">
        <Sparkles className="h-3.5 w-3.5 text-gold-500 shrink-0" />
        {billingEnabled
          ? 'Pagos procesados de forma segura por Mercado Pago. ' +
            'Cancela cuando quieras.'
          : 'El pago en línea estará disponible muy pronto. Mientras ' +
            'tanto activamos los planes manualmente — escríbenos.'}
      </p>
    </div>
  )
}

export function Account() {
  useDocumentTitle('Mi cuenta')
  const { user } = useAuthStore()
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-black text-gray-900">Mi cuenta</h1>
        <p className="text-gray-500 mt-1">
          Administra tu perfil y tu plan de suscripción.
        </p>
      </div>

      <div className="space-y-6">
        <ProfileSection key={user?.id ?? 'loading'} />
        <PlansSection />
      </div>
    </div>
  )
}
