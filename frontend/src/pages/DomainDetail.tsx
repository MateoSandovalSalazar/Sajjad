import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Play, Download, Copy, CheckCheck,
  RefreshCw, Clock, Globe, ShieldAlert,
} from 'lucide-react'
import { domainsApi } from '../api/domains'
import { scansApi } from '../api/scans'
import { getErrorMessage } from '../lib/errors'
import { toast } from '../store/toast'
import { RiskScoreGauge } from '../components/RiskScoreGauge'
import { RiskTrendChart } from '../components/RiskTrendChart'
import { FindingCard } from '../components/FindingCard'
import { UpgradeBanner } from '../components/UpgradeBanner'
import { Badge } from '../components/ui/Badge'
import { Spinner } from '../components/ui/Spinner'
import { usePlan } from '../hooks/usePlan'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import type { Scan, Severity } from '../types'

const STAGE_LABELS: Record<string, string> = {
  discovery:    'Descubriendo subdominios...',
  dns:          'Analizando DNS...',
  http:         'Probando servicios web...',
  ports:        'Escaneando puertos...',
  tls:          'Revisando certificados...',
  email:        'Analizando configuración de email...',
  vulns:        'Buscando vulnerabilidades...',
  osint:        'Consultando bases de datos externas...',
  scoring:      'Calculando riesgo...',
  complete:     'Completado',
}

function VerificationPanel({ domainId, fqdn, token }:
  { domainId: string; fqdn: string; token: string }) {
  const [copied, setCopied] = useState(false)
  const qc = useQueryClient()

  const verify = useMutation({
    mutationFn: () => domainsApi.verify(domainId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['domain', domainId] })
      toast.success('¡Dominio verificado! Ya puedes escanearlo.')
    },
  })

  const copy = () => {
    navigator.clipboard.writeText(token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="card p-6 border-l-4 border-amber-400">
      <h3 className="font-bold text-gray-900 mb-1 flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-amber-500" />
        Verifica que eres dueño del dominio
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Para proteger tu privacidad, necesitamos confirmar que controlas{' '}
        <strong>{fqdn}</strong>. Solo toma 2 minutos.
      </p>

      <div className="bg-gray-50 rounded-xl p-4 mb-4 space-y-3">
        <p className="text-sm font-semibold text-gray-700">
          1. Ve a la configuración DNS de tu dominio (GoDaddy, Cloudflare, etc.)
        </p>
        <p className="text-sm font-semibold text-gray-700">
          2. Agrega un registro de tipo <code className="bg-white px-1.5 py-0.5
            rounded border text-xs">TXT</code> con estos valores:
        </p>
        <div className="bg-white rounded-lg border p-3 space-y-2">
          <div className="flex justify-between text-xs items-center">
            <span className="text-gray-500">Tipo</span>
            <code className="bg-sand-50 px-1.5 py-0.5 rounded border">TXT</code>
          </div>
          <div className="flex justify-between text-xs items-center">
            <span className="text-gray-500">Nombre / Host</span>
            <div className="text-right">
              <code className="bg-sand-50 px-1.5 py-0.5 rounded border">@</code>
              <span className="block text-[11px] text-gray-400 mt-0.5">
                la raíz de <strong>{fqdn}</strong> (algunos proveedores
                usan «@» o lo dejan vacío)
              </span>
            </div>
          </div>
          <div className="flex justify-between text-xs items-center">
            <span className="text-gray-500">Valor</span>
            <div className="flex items-center gap-2">
              <code className="text-xs">{token}</code>
              <button onClick={copy} title="Copiar valor"
                className="text-obsidian-700 hover:text-obsidian-800">
                {copied
                  ? <CheckCheck className="h-4 w-4 text-green-500" />
                  : <Copy className="h-4 w-4" />
                }
              </button>
            </div>
          </div>
        </div>
        <p className="text-sm font-semibold text-gray-700">
          3. Espera 1-5 minutos y haz clic en "Verificar"
        </p>
      </div>

      {verify.isError && (
        <p className="text-sm text-red-600 mb-3">
          No se encontró el registro DNS. Asegúrate de haberlo guardado y
          espera unos minutos para que propague.
        </p>
      )}

      <button onClick={() => verify.mutate()}
        disabled={verify.isPending}
        className="btn-primary flex items-center gap-2">
        {verify.isPending ? <Spinner size="sm" /> : <CheckCheck className="h-4 w-4" />}
        {verify.isPending ? 'Verificando...' : 'Ya lo agregué, verificar'}
      </button>
    </div>
  )
}

function ScanProgress({ scan }: { scan: Scan }) {
  const STAGES = ['discovery','dns','http','ports','tls','email','vulns','osint','scoring','complete']
  const idx = STAGES.indexOf(scan.progress_stage ?? '')
  const pct = idx >= 0 ? Math.round(((idx + 1) / STAGES.length) * 100) : 10

  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-4">
        <RefreshCw className="h-5 w-5 text-obsidian-700 animate-spin" />
        <div>
          <p className="font-bold text-gray-900">Escaneo en progreso</p>
          <p className="text-sm text-gray-500">
            {STAGE_LABELS[scan.progress_stage ?? ''] ?? 'Iniciando...'}
          </p>
        </div>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div className="bg-obsidian-700 h-2 rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-400 mt-2">{pct}% completado</p>
    </div>
  )
}

export function DomainDetail() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const { caps } = usePlan()
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { data: domain, isLoading: loadingDomain } = useQuery({
    queryKey: ['domain', id],
    queryFn: () => domainsApi.get(id!).then(r => r.data),
  })

  useDocumentTitle(domain?.fqdn ?? 'Dominio')

  const { data: scans, isLoading: loadingScans } = useQuery({
    queryKey: ['scans', id],
    queryFn: () => scansApi.listByDomain(id!).then(r => r.data),
    enabled: !!domain?.is_verified,
  })

  const lastScan = scans?.[0]
  const isRunning = lastScan?.status === 'pending' || lastScan?.status === 'running'

  // Solo pedimos los hallazgos si el plan permite verlos (free no).
  const { data: scanDetail } = useQuery({
    queryKey: ['scan-detail', lastScan?.id],
    queryFn: () => scansApi.getWithFindings(lastScan!.id).then(r => r.data),
    enabled: lastScan?.status === 'completed' && caps.can_see_findings,
  })

  // Poll mientras corre el scan
  useEffect(() => {
    if (isRunning) {
      pollingRef.current = setInterval(() => {
        qc.invalidateQueries({ queryKey: ['scans', id] })
      }, 4000)
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current) }
  }, [isRunning, id, qc])

  const launchScan = useMutation({
    mutationFn: () => scansApi.launch(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scans', id] })
      toast.info('Escaneo iniciado. Esto puede tardar unos minutos.')
    },
    onError: (err) =>
      toast.error(getErrorMessage(err, 'No se pudo iniciar el escaneo.')),
  })

  const downloadPdf = async () => {
    try {
      const url = scansApi.pdfUrl(lastScan!.id)
      const token = localStorage.getItem('access_token')
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('pdf failed')
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = `sajjad-${domain?.fqdn}-reporte.pdf`
      a.click()
      URL.revokeObjectURL(objectUrl)
    } catch {
      toast.error('No se pudo descargar el reporte PDF.')
    }
  }

  if (loadingDomain) return (
    <div className="flex items-center justify-center h-64"><Spinner size="lg" /></div>
  )
  if (!domain) return (
    <p className="text-gray-500">Dominio no encontrado.</p>
  )

  const findings = scanDetail?.findings ?? []
  const bySeverity = (['critical','high','medium','low','info'] as Severity[])
    .reduce((acc, sev) => ({
      ...acc,
      [sev]: findings.filter(f => f.severity === sev),
    }), {} as Record<Severity, typeof findings>)

  return (
    <div>
      {/* Breadcrumb */}
      <Link to="/dashboard" className="inline-flex items-center gap-1 text-sm
        text-gray-500 hover:text-gray-900 mb-6 transition-colors">
        <ArrowLeft className="h-4 w-4" />
        Dashboard
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6 flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-obsidian-700" />
            <h1 className="text-2xl font-black text-gray-900">{domain.fqdn}</h1>
          </div>
          <p className="text-gray-500 text-sm mt-1">
            {domain.is_verified
              ? 'Dominio verificado · Monitoreo activo'
              : 'Pendiente de verificación'}
          </p>
        </div>

        {domain.is_verified && (
          <div className="flex gap-2 flex-wrap">
            {lastScan?.status === 'completed' && caps.can_download_pdf && (
              <button onClick={downloadPdf}
                className="btn-secondary flex items-center gap-2">
                <Download className="h-4 w-4" />
                Descargar reporte PDF
              </button>
            )}
            <button
              onClick={() => launchScan.mutate()}
              disabled={launchScan.isPending || isRunning}
              className="btn-primary flex items-center gap-2">
              {launchScan.isPending || isRunning
                ? <Spinner size="sm" />
                : <Play className="h-4 w-4" />
              }
              {isRunning ? 'Escaneando...' : 'Escanear ahora'}
            </button>
          </div>
        )}
      </div>

      {/* Verificación pendiente */}
      {!domain.is_verified && (
        <VerificationPanel domainId={domain.id} fqdn={domain.fqdn}
          token={domain.verification_token} />
      )}

      {/* Scan en progreso */}
      {isRunning && lastScan && <ScanProgress scan={lastScan} />}

      {/* Resultados */}
      {lastScan?.status === 'completed' && lastScan.risk_score !== null && (
        <div className="space-y-6">
          {/* Score + stats */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <div className="flex justify-center">
              <RiskScoreGauge score={lastScan.risk_score}
                level={lastScan.risk_level ?? 'low'} size="lg" />
            </div>
            <div className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Subdominios', value: lastScan.subdomains_count, icon: '🌐' },
                { label: 'Hosts activos', value: lastScan.live_hosts_count, icon: '💻' },
                { label: 'Puertos abiertos', value: lastScan.open_ports_count, icon: '🔌' },
                { label: 'Hallazgos', value: lastScan.findings_count, icon: '⚠️' },
              ].map(({ label, value, icon }) => (
                <div key={label} className="card p-4 text-center">
                  <span className="text-2xl">{icon}</span>
                  <p className="text-2xl font-black text-obsidian-700 mt-1">{value}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{label}</p>
                </div>
              ))}

              {/* Severity summary */}
              {lastScan.findings_summary && (
                <div className="col-span-2 sm:col-span-4 card p-4">
                  <p className="text-xs font-bold uppercase tracking-wider
                    text-gray-400 mb-3">
                    Hallazgos por severidad
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    {(['critical','high','medium','low','info'] as Severity[]).map(sev => (
                      <div key={sev} className="flex items-center gap-1.5">
                        <Badge level={sev} size="sm" />
                        <span className="text-sm font-bold text-gray-700">
                          {lastScan.findings_summary?.[sev] ?? 0}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Tendencia histórica */}
          {scans && <RiskTrendChart scans={scans} />}

          {/* Scan info */}
          {lastScan.completed_at && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Clock className="h-3.5 w-3.5" />
              Escaneo completado el{' '}
              {new Date(lastScan.completed_at).toLocaleString('es-MX')}
            </div>
          )}

          {/* Findings — bloqueados en plan free */}
          {!caps.can_see_findings ? (
            <UpgradeBanner
              title={`Tu escaneo encontró ${lastScan.findings_count} hallazgo${
                lastScan.findings_count !== 1 ? 's' : ''}`}
              desc="Tu plan actual solo muestra el Risk Score. Mejora tu plan
                para ver el detalle de cada hallazgo, cómo remediarlo y
                descargar el reporte PDF completo."
            />
          ) : findings.length > 0 ? (
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                Hallazgos de seguridad
              </h2>
              {loadingScans && <Spinner />}
              <div className="space-y-6">
                {(['critical','high','medium','low','info'] as Severity[]).map(sev =>
                  bySeverity[sev]?.length > 0 ? (
                    <div key={sev}>
                      <div className="flex items-center gap-2 mb-3">
                        <Badge level={sev} />
                        <span className="text-sm text-gray-500">
                          {bySeverity[sev].length} hallazgo{bySeverity[sev].length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <div className="space-y-2">
                        {bySeverity[sev].map(f =>
                          <FindingCard key={f.id} finding={f} />
                        )}
                      </div>
                    </div>
                  ) : null
                )}
              </div>
            </div>
          ) : (
            <div className="card p-10 text-center">
              <p className="text-4xl mb-3">🛡️</p>
              <h3 className="font-bold text-gray-900 mb-1">
                Sin hallazgos de seguridad
              </h3>
              <p className="text-sm text-gray-500">
                No se detectaron problemas en este escaneo. ¡Buen trabajo!
              </p>
            </div>
          )}
        </div>
      )}

      {/* Sin escaneos */}
      {domain.is_verified && !loadingScans && !lastScan && !isRunning && (
        <div className="card p-12 text-center mt-6">
          <Play className="h-12 w-12 text-gray-200 mx-auto mb-4" />
          <h3 className="font-bold text-gray-900 mb-2">
            Aún no has escaneado este dominio
          </h3>
          <p className="text-sm text-gray-500 mb-6">
            El primer escaneo tarda entre 1 y 5 minutos dependiendo del tamaño
            de tu empresa.
          </p>
          <button onClick={() => launchScan.mutate()}
            disabled={launchScan.isPending}
            className="btn-primary inline-flex items-center gap-2 py-3 px-6">
            {launchScan.isPending ? <Spinner size="sm" /> : <Play className="h-4 w-4" />}
            Iniciar primer escaneo
          </button>
        </div>
      )}
    </div>
  )
}
