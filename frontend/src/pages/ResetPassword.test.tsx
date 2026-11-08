import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { ResetPassword } from './ResetPassword'
import { ForgotPassword } from './ForgotPassword'
import { authApi } from '../api/auth'

vi.mock('../api/auth', () => ({
  authApi: {
    forgotPassword: vi.fn(),
    resetPassword: vi.fn(),
  },
}))
vi.mock('../hooks/useDocumentTitle', () => ({
  useDocumentTitle: () => {},
}))
vi.mock('../store/toast', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

const forgot = vi.mocked(authApi.forgotPassword)
const reset = vi.mocked(authApi.resetPassword)

function renderReset(search: string) {
  return render(
    <MemoryRouter initialEntries={[`/reset-password${search}`]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/login" element={<div>pantalla de login</div>} />
        <Route path="/forgot-password" element={<div>pedir enlace</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ResetPassword', () => {
  it('rechaza el enlace sin token sin llamar a la API', () => {
    renderReset('')

    expect(screen.getByText(/enlace inválido/i)).toBeInTheDocument()
    expect(reset).not.toHaveBeenCalled()
  })

  it('envía el token y la contraseña nueva, y lleva al login', async () => {
    reset.mockResolvedValue({ data: { message: 'ok' } } as never)
    renderReset('?token=tok-123')

    await userEvent.type(
      screen.getByLabelText('Nueva contraseña'), 'Tormenta7Azul',
    )
    await userEvent.type(
      screen.getByLabelText('Repetir contraseña'), 'Tormenta7Azul',
    )
    await userEvent.click(
      screen.getByRole('button', { name: /guardar contraseña/i }),
    )

    await waitFor(() =>
      expect(reset).toHaveBeenCalledWith('tok-123', 'Tormenta7Azul'),
    )
    expect(await screen.findByText(/pantalla de login/i)).toBeInTheDocument()
  })

  it('no envía nada si las contraseñas no coinciden', async () => {
    renderReset('?token=tok-123')

    await userEvent.type(
      screen.getByLabelText('Nueva contraseña'), 'Tormenta7Azul',
    )
    await userEvent.type(
      screen.getByLabelText('Repetir contraseña'), 'OtraCosa9Azul',
    )
    await userEvent.click(
      screen.getByRole('button', { name: /guardar contraseña/i }),
    )

    expect(await screen.findByText(/no coinciden/i)).toBeInTheDocument()
    expect(reset).not.toHaveBeenCalled()
  })

  it('bloquea contraseñas débiles antes de salir a la red', async () => {
    renderReset('?token=tok-123')

    await userEvent.type(
      screen.getByLabelText('Nueva contraseña'), 'todominusculas1',
    )
    await userEvent.type(
      screen.getByLabelText('Repetir contraseña'), 'todominusculas1',
    )
    await userEvent.click(
      screen.getByRole('button', { name: /guardar contraseña/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(/mayúscula/i)
    expect(reset).not.toHaveBeenCalled()
  })

  it('limpia los tokens guardados tras restablecer', async () => {
    // El backend sube token_version al restablecer, así que cualquier
    // sesión guardada en este navegador queda muerta.
    localStorage.setItem('access_token', 'viejo')
    localStorage.setItem('refresh_token', 'viejo-refresh')
    reset.mockResolvedValue({ data: { message: 'ok' } } as never)

    renderReset('?token=tok-123')
    await userEvent.type(
      screen.getByLabelText('Nueva contraseña'), 'Tormenta7Azul',
    )
    await userEvent.type(
      screen.getByLabelText('Repetir contraseña'), 'Tormenta7Azul',
    )
    await userEvent.click(
      screen.getByRole('button', { name: /guardar contraseña/i }),
    )

    await waitFor(() =>
      expect(localStorage.getItem('access_token')).toBeNull(),
    )
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })

  it('muestra el mensaje del backend si el token caducó', async () => {
    reset.mockRejectedValue({
      response: { data: { error: 'Unauthorized', message: 'Token used' } },
    })
    renderReset('?token=caducado')

    await userEvent.type(
      screen.getByLabelText('Nueva contraseña'), 'Tormenta7Azul',
    )
    await userEvent.type(
      screen.getByLabelText('Repetir contraseña'), 'Tormenta7Azul',
    )
    await userEvent.click(
      screen.getByRole('button', { name: /guardar contraseña/i }),
    )

    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})

describe('ForgotPassword', () => {
  it('confirma el envío sin revelar si el correo existe', async () => {
    forgot.mockResolvedValue({ data: { message: 'ok' } } as never)
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    )

    await userEvent.type(
      screen.getByLabelText(/correo/i), 'alguien@empresa.com',
    )
    await userEvent.click(
      screen.getByRole('button', { name: /enviar enlace/i }),
    )

    await waitFor(() =>
      expect(forgot).toHaveBeenCalledWith('alguien@empresa.com'),
    )
    // El texto es el mismo exista o no la cuenta: "Si <correo> está
    // registrado...". Nunca confirma ni niega que exista.
    expect(screen.getByText(/revisa tu correo/i)).toBeInTheDocument()
    expect(
      screen.getByText(/está\s+registrado/i),
    ).toBeInTheDocument()
  })
})
