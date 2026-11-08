import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { TrialBanner } from './TrialBanner'
import { usePlan } from '../hooks/usePlan'

vi.mock('../hooks/usePlan', () => ({ usePlan: vi.fn() }))

const mockedPlan = vi.mocked(usePlan)

function planState(over: Partial<ReturnType<typeof usePlan>> = {}) {
  return {
    plan: 'trial',
    planLabel: 'Prueba gratuita',
    caps: {
      max_domains: 3,
      max_scans_per_month: 10,
      scan_interval_days: 1,
      can_download_pdf: true,
      can_see_findings: true,
      white_label: false,
    },
    isTrial: true,
    trialDaysLeft: 3,
    billingEnabled: false,
    subscription: undefined,
    isLoading: false,
    ...over,
  } as ReturnType<typeof usePlan>
}

function renderBanner() {
  return render(
    <MemoryRouter>
      <TrialBanner />
    </MemoryRouter>,
  )
}

beforeEach(() => vi.clearAllMocks())

describe('TrialBanner', () => {
  it('avisa cuando quedan pocos días', () => {
    mockedPlan.mockReturnValue(planState({ trialDaysLeft: 3 }))
    renderBanner()
    expect(screen.getByText(/termina en 3 días/i)).toBeInTheDocument()
  })

  it('usa singular con un solo día', () => {
    mockedPlan.mockReturnValue(planState({ trialDaysLeft: 1 }))
    renderBanner()
    expect(screen.getByText(/termina en 1 día\./i)).toBeInTheDocument()
  })

  it('dice "hoy" cuando ya no quedan días', () => {
    mockedPlan.mockReturnValue(planState({ trialDaysLeft: 0 }))
    renderBanner()
    expect(screen.getByText(/termina hoy/i)).toBeInTheDocument()
  })

  it('no molesta al principio de la prueba', () => {
    // Mostrarlo los 14 días lo convierte en ruido que el usuario
    // deja de ver justo cuando importa.
    mockedPlan.mockReturnValue(planState({ trialDaysLeft: 12 }))
    const { container } = renderBanner()
    expect(container).toBeEmptyDOMElement()
  })

  it('no aparece si el usuario no está en prueba', () => {
    mockedPlan.mockReturnValue(
      planState({ isTrial: false, trialDaysLeft: null }),
    )
    const { container } = renderBanner()
    expect(container).toBeEmptyDOMElement()
  })

  it('ofrece "Ver planes" mientras no se pueda pagar', () => {
    mockedPlan.mockReturnValue(
      planState({ trialDaysLeft: 2, billingEnabled: false }),
    )
    renderBanner()
    expect(screen.getByRole('link', { name: /ver planes/i }))
      .toHaveAttribute('href', '/account')
  })

  it('ofrece "Mejorar mi plan" cuando los pagos están activos', () => {
    mockedPlan.mockReturnValue(
      planState({ trialDaysLeft: 2, billingEnabled: true }),
    )
    renderBanner()
    expect(
      screen.getByRole('link', { name: /mejorar mi plan/i }),
    ).toBeInTheDocument()
  })
})
