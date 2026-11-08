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

  // Pasa por la instancia con interceptores, así que si el access
  // token caducó se refresca y se reintenta solo.
  pdf: (id: string) =>
    api.get<Blob>(`/scans/${id}/pdf`, { responseType: 'blob' }),
}
