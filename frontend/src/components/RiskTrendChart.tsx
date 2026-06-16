import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from 'recharts'
import type { Scan } from '../types'

interface Props { scans: Scan[] }

const LEVEL_COLOR: Record<string, string> = {
  critical: '#dc2626',
  high:     '#ea580c',
  medium:   '#d97706',
  low:      '#2563eb',
}

interface Point {
  date: string
  score: number
  level: string
}

function TooltipBox({ active, payload }: {
  active?: boolean
  payload?: { payload: Point }[]
}) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="bg-obsidian-900 text-white rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="font-bold text-gold-400">{p.score}/100</p>
      <p className="text-white/60">{p.date}</p>
    </div>
  )
}

export function RiskTrendChart({ scans }: Props) {
  // Solo scans completados con score, en orden cronológico ascendente.
  const points: Point[] = scans
    .filter(s => s.status === 'completed' && s.risk_score !== null)
    .slice()
    .reverse()
    .map(s => ({
      date: new Date(s.completed_at ?? s.started_at)
        .toLocaleDateString('es-MX', { day: '2-digit', month: 'short' }),
      score: s.risk_score as number,
      level: s.risk_level ?? 'low',
    }))

  // Con menos de 2 puntos no hay tendencia que mostrar.
  if (points.length < 2) return null

  const latest = points[points.length - 1]
  const stroke = LEVEL_COLOR[latest.level] ?? '#2563eb'
  const first = points[0].score
  const delta = latest.score - first

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            Evolución del riesgo
          </h2>
          <p className="text-sm text-gray-500">
            Risk Score a lo largo de tus últimos {points.length} escaneos
          </p>
        </div>
        {delta !== 0 && (
          <span className={`text-sm font-bold px-2.5 py-1 rounded-full ${
            delta > 0
              ? 'bg-red-50 text-red-600'
              : 'bg-green-50 text-green-600'
          }`}>
            {delta > 0 ? '▲' : '▼'} {Math.abs(delta)} pts
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={points} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity={0.25} />
              <stop offset="100%" stopColor={stroke} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }}
            axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]}
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            axisLine={false} tickLine={false} />
          <Tooltip content={<TooltipBox />} />
          {/* Umbrales de severidad como guía visual. */}
          <ReferenceLine y={75} stroke="#fca5a5" strokeDasharray="4 4" />
          <ReferenceLine y={50} stroke="#fcd34d" strokeDasharray="4 4" />
          <Area type="monotone" dataKey="score" stroke={stroke}
            strokeWidth={2.5} fill="url(#riskFill)"
            dot={{ r: 3, fill: stroke }}
            activeDot={{ r: 5 }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
