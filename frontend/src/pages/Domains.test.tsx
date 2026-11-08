import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

import { Domains } from './Domains'
import { domainsApi } from '../api/domains'

vi.mock('../api/domains', () => ({
  domainsApi: {
    list: vi.fn(),
    create: vi.fn(),
    delete: vi.fn(),
  },
}))
vi.mock('../hooks/useDocumentTitle', () => ({
  useDocumentTitle: () => {},
}))
vi.mock('../store/toast', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

const list = vi.mocked(domainsApi.list)
const create = vi.mocked(domainsApi.create)

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Domains />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  list.mockResolvedValue({ data: [] } as never)
})

describe('Alta de dominio — autorización', () => {
  it('no deja agregar sin declarar la propiedad', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', {
      name: /agregar dominio/i,
    }))
    await user.type(
      screen.getByPlaceholderText(/empresa\.com/i),
      'ejemplo.com',
    )

    // Con el dominio escrito pero la casilla sin marcar, el botón
    // sigue bloqueado: escanear infraestructura sin declaración de
    // propiedad es exactamente lo que el producto no debe permitir.
    const agregar = screen.getByRole('button', { name: /^agregar$/i })
    expect(agregar).toBeDisabled()

    await user.click(agregar)
    expect(create).not.toHaveBeenCalled()
  })

  it('envía authorized=true al marcar la casilla', async () => {
    const user = userEvent.setup()
    create.mockResolvedValue({
      data: {
        id: 'd1',
        fqdn: 'ejemplo.com',
        is_verified: false,
        verification_token: 'sajjad-verify-abc',
        verified_at: null,
        created_at: '2026-08-05T00:00:00Z',
      },
    } as never)

    renderPage()

    await user.click(await screen.findByRole('button', {
      name: /agregar dominio/i,
    }))
    await user.type(
      screen.getByPlaceholderText(/empresa\.com/i),
      'ejemplo.com',
    )
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: /^agregar$/i }))

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith('ejemplo.com', true))
  })

  it('muestra el texto de la declaración de propiedad', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', {
      name: /agregar dominio/i,
    }))

    expect(
      screen.getByText(/soy el propietario de este dominio/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/autorización expresa por escrito/i),
    ).toBeInTheDocument()
  })

  it('normaliza el dominio antes de enviarlo', async () => {
    const user = userEvent.setup()
    create.mockResolvedValue({ data: { id: 'd1' } } as never)
    renderPage()

    await user.click(await screen.findByRole('button', {
      name: /agregar dominio/i,
    }))
    await user.type(
      screen.getByPlaceholderText(/empresa\.com/i),
      '  EJEMPLO.com  ',
    )
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: /^agregar$/i }))

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith('ejemplo.com', true))
  })
})
