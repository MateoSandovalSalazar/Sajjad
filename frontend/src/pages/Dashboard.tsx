import { useQuery, useQueries } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Globe, Plus, ChevronRight, ShieldCheck, AlertTriangle } from 'lucide-react'
import { domainsApi } from '../api/domains'
import { scansApi } from '../api/scans'
import { useAuthStore } from '../store/auth'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { RiskScoreGauge } from '../components/RiskScoreGauge'
import { Badge } from '../components/ui/Badge'
import { Spinner } from '../components/ui/Spinner'
import type { Domain, Scan } from '../types'

function DomainCard({ domain, last }: { domain: Domain; last?: Scan | null }) {
  return (
    <Link to={`/domains/${domain.id}`}
      className="card p-5 flex items-center gap-4 hover:shadow-md
        hover:border-obsidian-100 transition-all duration-200 group">
      {last?.status === 'completed' && last.risk_score !== null ? (
        <RiskScoreGauge score={last.risk_score}
          level={last.risk_level ?? 'low'} size="sm" />
      ) : (
        <div className="w-28 h-28 rounded-2xl bg-gray-100 border-2
          border-gray-200 flex flex-col items-center justify-center">
          {!domain.is_verified ? (
            <>
              <AlertTriangle className="h-6 w-6 text-amber-400 mb-1" />
              <span className="text-xs text-gray-500 text-center px-2">
                Sin verificar
              </span>
            </>
          ) : (
            <>
              <Globe className="h-6 w-6 text-gray-300 mb-1" />
              <span className="text-xs text-gray-400">Sin escanear</span>
            </>
          )}
        </div>
      )}

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-bold text-gray-900 truncate">{domain.fqdn}</h3>
          {domain.is_verified
            ? <ShieldCheck className="h-4 w-4 text-green-500 shrink-0" />
            : <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
          }
        </div>

        {last?.status === 'completed' && last.findings_summary ? (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {(['critical','high','medium','low'] as const).map(sev =>
              (last.findings_summary?.[sev] ?? 0) > 0 ? (
                <span key={sev} className="text-xs">
                  <Badge level={sev} size="sm" />
                  <span className="ml-1 text-gray-600">
                    {last.findings_summary?.[sev]}
                  </span>
                </span>
              ) : null
            )}
            {Object.values(last.findings_summary).every(v => v === 0) && (
              <Badge level="safe" size="sm" />
            )}
          </div>
        ) : !domain.is_verified ? (
          <p className="text-xs text-amber-600 mt-1">
            Verificación DNS pendiente
          </p>
        ) : (
          <p className="text-xs text-gray-400 mt-1">
            {last?.status === 'running' || last?.status === 'pending'
              ? 'Escaneo en progreso...'
              : 'Haz clic para escanear'}
          </p>
        )}

        {last?.completed_at && (
          <p className="text-xs text-gray-400 mt-1">
            Último scan: {new Date(last.completed_at).toLocaleDateString('es-MX')}
          </p>
        )}
      </div>

      <ChevronRight className="h-5 w-5 text-gray-300
        group-hover:text-obsidian-700 transition-colors shrink-0" />
    </Link>
  )
}

function SummaryBar({ scans }: { scans: Scan[] }) {
  const completed = scans.filter(s => s.status === 'completed')
  if (completed.length === 0) return null

  const avgScore = Math.round(
    completed.reduce((a, s) => a + (s.risk_score ?? 0), 0) / completed.length
  )
  const worst = completed.reduce<Scan | null>((a, s) =>
    (s.risk_score ?? 0) > (a?.risk_score ?? 0) ? s : a, null)

  const totalFindings = completed.reduce((a, s) => a + s.findings_count, 0)

  return (
    <div className="grid grid-cols-3 gap-4 mb-8">
      {[
        { label: 'Score promedio', value: `${avgScore}/100`,
          sub: 'riesgo general', color: 'text-obsidian-700' },
        { label: 'Hallazgos activos', value: totalFindings,
          sub: 'en todos tus dominios', color: 'text-gold-600' },
        { label: 'Dominio más crítico', value: worst?.risk_score ?? '—',
          sub: worst ? `de 100` : 'sin datos', color: 'text-red-600' },
      ].map(({ label, value, sub, color }) => (
        <div key={label} className="card p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
            {label}
          </p>
          <p className={`text-2xl font-black ${color}`}>{value}</p>
          <p className="text-xs text-gray-400">{sub}</p>
        </div>
      ))}
    </div>
  )
}

export function Dashboard() {
  useDocumentTitle('Panel')
  const { user } = useAuthStore()

  const { data: domains, isLoading } = useQuery({
    queryKey: ['domains'],
    queryFn: () => domainsApi.list().then(r => r.data),
  })

  // Traemos el historial de scans de cada dominio una sola vez. Alimenta
  // tanto el resumen agregado como cada tarjeta (sin fetches duplicados).
  const scanResults = useQueries({
    queries: (domains ?? []).map(d => ({
      queryKey: ['scans', d.id],
      queryFn: () => scansApi.listByDomain(d.id).then(r => r.data),
      enabled: d.is_verified,
    })),
  })

  const lastByDomain = new Map<string, Scan | undefined>()
  ;(domains ?? []).forEach((d, i) => {
    lastByDomain.set(d.id, scanResults[i]?.data?.[0])
  })
  const lastScans = Array.from(lastByDomain.values())
    .filter((s): s is Scan => !!s)

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <Spinner size="lg" />
    </div>
  )

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Buenos días' : hour < 19 ? 'Buenas tardes' : 'Buenas noches'

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-black text-gray-900">
            {greeting}, {user?.full_name?.split(' ')[0] ?? 'usuario'} 👋
          </h1>
          <p className="text-gray-500 mt-1">
            Aquí está el estado de seguridad de tu empresa.
          </p>
        </div>
        <Link to="/domains" className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Agregar dominio
        </Link>
      </div>

      {/* Empty state */}
      {(!domains || domains.length === 0) ? (
        <div className="card p-16 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16
            bg-obsidian-50 rounded-2xl mb-4">
            <Globe className="h-8 w-8 text-obsidian-700" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Agrega tu primer dominio
          </h2>
          <p className="text-gray-500 max-w-sm mx-auto mb-6">
            Sajjad analizará qué tiene expuesto tu empresa en internet y
            te dirá exactamente qué corregir.
          </p>
          <Link to="/domains" className="btn-primary inline-flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Agregar dominio
          </Link>
        </div>
      ) : (
        <>
          <SummaryBar scans={lastScans} />

          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-gray-900">Tus dominios</h2>
            <span className="text-sm text-gray-400">
              {domains.length} dominio{domains.length !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="space-y-3">
            {domains.map(d =>
              <DomainCard key={d.id} domain={d} last={lastByDomain.get(d.id)} />
            )}
          </div>
        </>
      )}
    </div>
  )
}
