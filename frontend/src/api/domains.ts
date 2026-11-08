import { api } from './client'
import type { Domain } from '../types'

export const domainsApi = {
  list: () => api.get<Domain[]>('/domains'),

  // `authorized` es la declaración de propiedad del dominio. El
  // backend la rechaza si no viene en true y registra fecha e IP.
  create: (fqdn: string, authorized: boolean) =>
    api.post<Domain>('/domains', { fqdn, authorized }),

  get: (id: string) => api.get<Domain>(`/domains/${id}`),

  verify: (id: string) =>
    api.post<Domain>(`/domains/${id}/verify`),

  delete: (id: string) => api.delete(`/domains/${id}`),
}
