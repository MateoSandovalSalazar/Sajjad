import { api } from './client'
import type { Domain } from '../types'

export const domainsApi = {
  list: () => api.get<Domain[]>('/domains'),

  create: (fqdn: string) => api.post<Domain>('/domains', { fqdn }),

  get: (id: string) => api.get<Domain>(`/domains/${id}`),

  verify: (id: string) =>
    api.post<{ message: string }>(`/domains/${id}/verify`),

  delete: (id: string) => api.delete(`/domains/${id}`),
}
