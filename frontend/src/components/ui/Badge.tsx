import type { Severity, RiskLevel } from '../../types'

const STYLES: Record<string, string> = {
  critical: 'bg-red-100 text-red-700 border border-red-200',
  high:     'bg-gold-100 text-gold-700 border border-gold-200',
  medium:   'bg-amber-100 text-amber-700 border border-amber-200',
  low:      'bg-blue-100 text-blue-700 border border-blue-200',
  info:     'bg-gray-100 text-gray-600 border border-gray-200',
  safe:     'bg-green-100 text-green-700 border border-green-200',
}

const LABELS: Record<string, string> = {
  critical: 'Crítico',
  high:     'Alto',
  medium:   'Medio',
  low:      'Bajo',
  info:     'Info',
  safe:     'Seguro',
}

interface Props {
  level: Severity | RiskLevel | 'safe'
  size?: 'sm' | 'md'
}

export function Badge({ level, size = 'md' }: Props) {
  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-xs'
  return (
    <span className={`inline-flex items-center font-bold rounded-full uppercase
      tracking-wide ${padding} ${STYLES[level] ?? STYLES.info}`}>
      {LABELS[level] ?? level}
    </span>
  )
}
