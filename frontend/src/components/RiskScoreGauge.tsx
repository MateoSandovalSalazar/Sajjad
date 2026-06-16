interface Props {
  score: number
  level: string
  size?: 'sm' | 'lg'
}

const LEVEL_CONFIG = {
  critical: { color: '#dc2626', label: 'Crítico', bg: 'bg-red-50',    border: 'border-red-200' },
  high:     { color: '#ea580c', label: 'Alto',     bg: 'bg-gold-50', border: 'border-gold-200' },
  medium:   { color: '#d97706', label: 'Medio',    bg: 'bg-amber-50',  border: 'border-amber-200' },
  low:      { color: '#2563eb', label: 'Bajo',     bg: 'bg-blue-50',   border: 'border-blue-200' },
} as const

export function RiskScoreGauge({ score, level, size = 'lg' }: Props) {
  const cfg   = LEVEL_CONFIG[level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.low
  const isLg  = size === 'lg'
  const r     = isLg ? 70 : 44
  const cx    = isLg ? 90 : 56
  const cy    = isLg ? 90 : 56
  const svgSz = isLg ? 180 : 112
  const circ  = 2 * Math.PI * r
  const dash  = (score / 100) * circ

  return (
    <div className={`flex flex-col items-center justify-center rounded-2xl border-2
      p-6 ${cfg.bg} ${cfg.border}`}>
      <svg width={svgSz} height={svgSz} viewBox={`0 0 ${svgSz} ${svgSz}`}>
        {/* Track */}
        <circle cx={cx} cy={cy} r={r} fill="none"
          stroke="#e5e7eb" strokeWidth={isLg ? 12 : 8} />
        {/* Progress */}
        <circle cx={cx} cy={cy} r={r} fill="none"
          stroke={cfg.color} strokeWidth={isLg ? 12 : 8}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          strokeDashoffset={circ * 0.25}
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
        {/* Score */}
        <text x={cx} y={cy - (isLg ? 6 : 4)} textAnchor="middle"
          fill={cfg.color} fontWeight="900"
          fontSize={isLg ? 36 : 22}>
          {score}
        </text>
        <text x={cx} y={cy + (isLg ? 18 : 12)} textAnchor="middle"
          fill="#6b7280" fontSize={isLg ? 11 : 9}>
          de 100
        </text>
      </svg>
      <span className="font-bold text-sm mt-1 uppercase tracking-widest"
        style={{ color: cfg.color }}>
        {cfg.label}
      </span>
    </div>
  )
}
