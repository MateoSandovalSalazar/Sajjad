export interface User {
  id: string
  email: string
  full_name: string
  company?: string
  is_verified: boolean
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  user_id: string
  email: string
  is_verified: boolean
}

export interface Domain {
  id: string
  fqdn: string
  is_verified: boolean
  verification_token: string
  verified_at: string | null
  created_at: string
  last_scan?: Scan | null
}

export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed'
export type RiskLevel  = 'critical' | 'high' | 'medium' | 'low'
export type Severity   = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface Scan {
  id: string
  domain_id: string
  status: ScanStatus
  progress_stage: string | null
  risk_score: number | null
  risk_level: RiskLevel | null
  subdomains_count: number
  live_hosts_count: number
  open_ports_count: number
  findings_count: number
  findings_summary: Record<Severity, number> | null
  started_at: string
  completed_at: string | null
}

export interface Finding {
  id: string
  category: string
  severity: Severity
  title: string
  description: string
  recommendation: string
  evidence: Record<string, unknown>
  source_tool: string
  host: string
  port: number | null
  cve: string | null
  cvss_score: number | null
  discovered_at: string
}

export interface ScanWithFindings extends Scan {
  findings: Finding[]
}

export interface Plan {
  id: string
  name: string
  price_usd: number
  domains: number
  scan_interval: string
  features: string[]
}

// Respuesta de GET /billing/plans
export interface PlanInfo {
  name: string
  price_usd: number
  max_domains: number
  max_scans_per_month: number
  scan_interval_days: number | null
  can_download_pdf: boolean
  white_label: boolean
}

// Respuesta de GET /billing/subscription
export interface Subscription {
  id: string
  plan: string
  status: string
  current_period_end: string | null
  scans_this_month: number
  created_at: string
}
