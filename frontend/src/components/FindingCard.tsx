import { ChevronDown, ChevronUp, AlertTriangle, Info } from 'lucide-react'
import { useState } from 'react'
import { Badge } from './ui/Badge'
import type { Finding } from '../types'

const CATEGORY_LABELS: Record<string, string> = {
  subdomain: 'Subdominio',
  port:      'Puerto',
  cert:      'Certificado',
  cred:      'Credencial',
  dns:       'DNS / Email',
  vuln:      'Vulnerabilidad',
  cloud:     'Cloud',
  osint:     'Inteligencia',
}

interface Props { finding: Finding }

export function FindingCard({ finding }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="card overflow-hidden transition-all duration-200">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left
          hover:bg-gray-50 transition-colors"
      >
        {finding.severity === 'info'
          ? <Info className="h-4 w-4 text-gray-400 shrink-0" />
          : <AlertTriangle className="h-4 w-4 text-gold-500 shrink-0" />
        }
        <Badge level={finding.severity} size="sm" />
        <span className="flex-1 font-semibold text-gray-900 text-sm">
          {finding.title}
        </span>
        <span className="text-xs text-gray-400 hidden sm:block">
          {CATEGORY_LABELS[finding.category] ?? finding.category}
        </span>
        {open
          ? <ChevronUp className="h-4 w-4 text-gray-400 shrink-0" />
          : <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
        }
      </button>

      {open && (
        <div className="border-t border-gray-100 px-5 py-4 space-y-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
              Host afectado
            </p>
            <code className="text-sm bg-gray-100 px-2 py-1 rounded">
              {finding.host}{finding.port ? `:${finding.port}` : ''}
            </code>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
              Qué significa
            </p>
            <p className="text-sm text-gray-700">{finding.description}</p>
          </div>
          <div className="bg-green-50 border border-green-100 rounded-xl px-4 py-3">
            <p className="text-xs font-bold uppercase tracking-wider text-green-700 mb-1">
              Qué hacer
            </p>
            <p className="text-sm text-green-800">{finding.recommendation}</p>
          </div>
          {finding.cve && (
            <span className="inline-block text-xs font-bold bg-obsidian-700 text-white
              px-2 py-1 rounded">
              {finding.cve}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
