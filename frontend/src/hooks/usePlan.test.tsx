import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { usePlan } from './usePlan'
import { billingApi } from '../api/billing'
import type { Subscription } from '../types'

vi.mock('../api/billing', () => ({
  billingApi: { subscription: vi.fn() },
}))

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

function subscription(over: Partial<Subscription> = {}): Subscription {
  return {
    id: 'sub-1',
    plan: 'professional',
    plan_label: 'Professional',
    status: 'active',
    capabilities: {
      max_domains: 3,
      max_scans_per_month: 30,
      scan_interval_days: 1,
      can_download_pdf: true,
      can_see_findings: true,
      white_label: false,
    },
    current_period_end: null,
    scans_this_month: 2,
    created_at: '2026-08-01T00:00:00Z',
    is_trial: false,
    trial_ends_at: null,
    trial_days_left: null,
    billing_enabled: false,
    ...over,
  }
}

const mocked = vi.mocked(billingApi.subscription)

beforeEach(() => vi.clearAllMocks())

describe('usePlan', () => {
  it('expone las capacidades que devuelve el backend', async () => {
    mocked.mockResolvedValue({ data: subscription() } as never)

    const { result } = renderHook(() => usePlan(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.plan).toBe('professional')
    expect(result.current.planLabel).toBe('Professional')
    expect(result.current.caps.max_domains).toBe(3)
    expect(result.current.caps.can_see_findings).toBe(true)
  })

  it('bloquea todo mientras carga', () => {
    // Nunca resuelve: simula la petición en vuelo.
    mocked.mockReturnValue(new Promise(() => {}) as never)

    const { result } = renderHook(() => usePlan(), { wrapper })

    // Por defecto lo más restrictivo: si aún no sabemos el plan, no
    // se le enseña de más al usuario.
    expect(result.current.caps.can_see_findings).toBe(false)
    expect(result.current.caps.can_download_pdf).toBe(false)
  })

  it('cae a lo más restrictivo si la petición falla', async () => {
    mocked.mockRejectedValue(new Error('500'))

    const { result } = renderHook(() => usePlan(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.plan).toBe('free')
    expect(result.current.caps.can_see_findings).toBe(false)
  })

  it('refleja el estado de la prueba gratuita', async () => {
    mocked.mockResolvedValue({
      data: subscription({
        plan: 'trial',
        plan_label: 'Prueba gratuita',
        is_trial: true,
        trial_days_left: 9,
      }),
    } as never)

    const { result } = renderHook(() => usePlan(), { wrapper })

    await waitFor(() => expect(result.current.isTrial).toBe(true))
    expect(result.current.trialDaysLeft).toBe(9)
  })

  it('informa si la pasarela de pagos está activa', async () => {
    mocked.mockResolvedValue({
      data: subscription({ billing_enabled: true }),
    } as never)

    const { result } = renderHook(() => usePlan(), { wrapper })

    await waitFor(() =>
      expect(result.current.billingEnabled).toBe(true))
  })
})
