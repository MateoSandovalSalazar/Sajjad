import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { VerifyPending } from './VerifyPending'
import { authApi } from '../api/auth'

vi.mock('../api/auth', () => ({
  authApi: { resendVerification: vi.fn() },
}))

const resend = vi.mocked(authApi.resendVerification)

function renderPage(search = '?email=ana%40empresa.com') {
  return render(
    <MemoryRouter initialEntries={[`/verify-pending${search}`]}>
      <VerifyPending />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('VerifyPending — reenvío del correo', () => {
  it('reenvía al correo que viene en la URL', async () => {
    resend.mockResolvedValue({ data: { message: 'ok' } } as never)
    renderPage()

    await userEvent.click(
      screen.getByRole('button', { name: /reenviar el correo/i }),
    )

    await waitFor(() =>
      expect(resend).toHaveBeenCalledWith('ana@empresa.com'),
    )
    expect(
      await screen.findByText(/te reenviamos el enlace/i),
    ).toBeInTheDocument()
  })

  it('no ofrece reenviar si no sabe a qué correo', () => {
    // Sin el parámetro `email` no hay destinatario que mandar.
    renderPage('')

    expect(
      screen.queryByRole('button', { name: /reenviar/i }),
    ).not.toBeInTheDocument()
  })

  it('muestra el error si el reenvío falla', async () => {
    resend.mockRejectedValue({
      response: {
        data: {
          error: 'RateLimitExceeded',
          message: 'Demasiados intentos.',
        },
      },
    })
    renderPage()

    await userEvent.click(
      screen.getByRole('button', { name: /reenviar el correo/i }),
    )

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    // El botón sigue disponible para reintentar más tarde.
    expect(
      screen.getByRole('button', { name: /reenviar el correo/i }),
    ).toBeInTheDocument()
  })

  it('oculta el botón tras un reenvío correcto', async () => {
    resend.mockResolvedValue({ data: { message: 'ok' } } as never)
    renderPage()

    await userEvent.click(
      screen.getByRole('button', { name: /reenviar el correo/i }),
    )

    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: /reenviar el correo/i }),
      ).not.toBeInTheDocument(),
    )
  })
})
