import { describe, it, expect } from 'vitest'
import { getErrorMessage } from './errors'

/** Construye un error de axios con el cuerpo que devolvería la API. */
function apiError(data: unknown) {
  return { response: { data } }
}

describe('getErrorMessage', () => {
  it('traduce los códigos de error conocidos', () => {
    expect(getErrorMessage(apiError({ error: 'Unauthorized' })))
      .toMatch(/contraseña incorrectos/i)

    expect(getErrorMessage(apiError({ error: 'ScanAlreadyRunning' })))
      .toMatch(/escaneo en curso/i)

    expect(getErrorMessage(apiError({ error: 'DomainNotVerified' })))
      .toMatch(/no está verificado/i)
  })

  it('explica que los pagos aún no están activos', () => {
    // El backend responde 503 BillingDisabled mientras
    // BILLING_ENABLED=false. El usuario no debe ver un error crudo.
    const msg = getErrorMessage(apiError({ error: 'BillingDisabled' }))
    expect(msg).toMatch(/no está disponible/i)
    expect(msg).not.toMatch(/BillingDisabled/)
  })

  it('distingue el límite de dominios del de escaneos', () => {
    const dominios = getErrorMessage(apiError({
      error: 'PlanLimitExceeded',
      message: 'Your free plan supports up to 1 domain(s).',
    }))
    expect(dominios).toMatch(/límite de dominios/i)

    const escaneos = getErrorMessage(apiError({
      error: 'PlanLimitExceeded',
      message: 'Monthly scan limit reached (1).',
    }))
    expect(escaneos).toMatch(/límite de escaneos/i)
  })

  it('reconoce el email sin verificar', () => {
    const msg = getErrorMessage(apiError({
      error: 'Forbidden',
      message: 'Email not verified. Check your inbox.',
    }))
    expect(msg).toMatch(/no está verificado/i)
  })

  it('nunca devuelve texto en inglés del backend para códigos conocidos', () => {
    // Regresión: los mensajes del backend están en inglés y se
    // mostraban tal cual en los toasts.
    const msg = getErrorMessage(apiError({
      error: 'Unauthorized',
      message: 'Incorrect email or password.',
    }))
    expect(msg).not.toMatch(/Incorrect email/)
  })

  it('extrae el detalle de los errores de validación de FastAPI', () => {
    expect(getErrorMessage(apiError({
      detail: [{ msg: 'Value error, Enter a valid domain.' }],
    }))).toBe('Enter a valid domain.')

    expect(getErrorMessage(apiError({ detail: 'Algo concreto' })))
      .toBe('Algo concreto')
  })

  it('cae al mensaje por defecto cuando no hay respuesta', () => {
    expect(getErrorMessage(new Error('network down')))
      .toMatch(/Algo salió mal/i)
    expect(getErrorMessage(undefined, 'Mensaje propio'))
      .toBe('Mensaje propio')
  })
})
