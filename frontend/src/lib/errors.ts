// Traduce los errores del backend (en inglés) a mensajes claros en español.
// El backend devuelve dos formas:
//   - Excepciones propias:   { error: "PlanLimitExceeded", message: "..." }
//   - Validación de FastAPI:  { detail: "..." | [{ msg: "..." }] }

interface ApiErrorBody {
  error?: string
  message?: string
  detail?: string | { msg?: string }[]
}

const CODE_ES: Record<string, string> = {
  Unauthorized:       'Email o contraseña incorrectos.',
  ScanAlreadyRunning: 'Ya hay un escaneo en curso para este dominio.',
  DomainNotVerified:  'El dominio no está verificado. Agrega el registro DNS TXT y verifícalo primero.',
  DomainAlreadyExists:'Ese dominio ya está registrado en tu cuenta.',
  NotFound:           'No se encontró el recurso solicitado.',
  ValidationError:    'Revisa los datos ingresados.',
  BillingDisabled:    'El pago en línea todavía no está disponible. ' +
                      'Escríbenos y activamos tu plan manualmente.',
}

/**
 * El mensaje que mandó el backend, tal cual.
 *
 * `getErrorMessage` traduce por código de error, que es lo correcto
 * cuando el backend responde en inglés y de forma genérica. Pero hay
 * caminos —la verificación DNS— donde el backend ya devuelve un
 * mensaje en español y específico ("el dominio no existe en el DNS"
 * vs. "no encontré el token"), y traducirlo por código lo
 * reemplazaría por uno más vago. Aquí se prefiere el del servidor.
 */
export function getServerMessage(
  err: unknown,
  fallback = 'Algo salió mal. Intenta de nuevo.',
): string {
  const body = (err as { response?: { data?: ApiErrorBody } })
    ?.response?.data
  if (body?.message) return body.message
  return getErrorMessage(err, fallback)
}

export function getErrorMessage(
  err: unknown,
  fallback = 'Algo salió mal. Intenta de nuevo.',
): string {
  const body = (err as { response?: { data?: ApiErrorBody } })
    ?.response?.data
  if (!body) return fallback

  // Límites de plan: traducir según el contexto (dominio vs escaneo).
  if (body.error === 'PlanLimitExceeded') {
    const m = body.message ?? ''
    if (/domain/i.test(m))
      return 'Alcanzaste el límite de dominios de tu plan. ' +
        'Mejora tu plan para agregar más.'
    if (/scan/i.test(m))
      return 'Alcanzaste el límite de escaneos de este mes. ' +
        'Mejora tu plan o espera al próximo mes.'
    return 'Esta función requiere un plan superior. Mejora tu plan.'
  }

  // Email sin verificar.
  if (body.error === 'Forbidden' && /verif/i.test(body.message ?? ''))
    return 'Tu correo aún no está verificado. Revisa tu bandeja de entrada.'

  // Código conocido.
  if (body.error && CODE_ES[body.error]) return CODE_ES[body.error]

  // Detalle de FastAPI.
  const d = body.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length > 0)
    return (d[0]?.msg ?? fallback).replace(/^Value error,\s*/i, '')

  // Último recurso: el mensaje crudo del backend.
  return body.message ?? fallback
}
