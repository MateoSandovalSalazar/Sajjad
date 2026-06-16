import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { toast } from '../store/toast'

const BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Instancia "desnuda" sin interceptores: la usamos para refrescar el
// token sin disparar recursión en el flujo de 401.
const bare = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// --- Refresh con cola de peticiones --------------------------------------
// Si varias peticiones fallan con 401 a la vez, solo lanzamos UN refresh
// y las demás esperan a que termine, reusando el token nuevo.
let refreshing: Promise<string> | null = null

function forceLogout(message?: string) {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  if (message) toast.error(message)
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

async function runRefresh(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('no refresh token')

  const { data } = await bare.post('/auth/refresh', {
    refresh_token: refreshToken,
  })
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  return data.access_token
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retried?: boolean })
      | undefined

    const isAuthCall = original?.url?.includes('/auth/')

    if (
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !isAuthCall
    ) {
      original._retried = true
      try {
        refreshing ??= runRefresh().finally(() => { refreshing = null })
        const newToken = await refreshing
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch {
        forceLogout('Tu sesión expiró. Inicia sesión de nuevo.')
      }
    }

    return Promise.reject(error)
  },
)
