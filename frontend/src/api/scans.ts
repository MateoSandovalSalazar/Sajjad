import { api } from './client'
import type { Scan, ScanWithFindings } from '../types'

export const scansApi = {
  launch: (domain_id: string) =>
    api.post<Scan>('/scans', { domain_id }),

  get: (id: string) => api.get<Scan>(`/scans/${id}`),

  getWithFindings: (id: string) =>
    api.get<ScanWithFindings>(`/scans/${id}/findings`),

  listByDomain: (domain_id: string) =>
    api.get<Scan[]>(`/domains/${domain_id}/scans`),

  pdfUrl: (id: string) =>
    `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'}/scans/${id}/pdf`,
}
