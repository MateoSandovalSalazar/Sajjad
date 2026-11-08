import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { MailCheck, RefreshCw } from 'lucide-react'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../lib/errors'
import { Spinner } from '../components/ui/Spinner'

export function VerifyPending() {
  const [params] = useSearchParams()
  const email = params.get('email')

  const [sending, setSending] = useState(false)
  const [resent, setResent]   = useState(false)
  const [error, setError]     = useState('')

  // El envío del correo en el registro es best-effort: si el SMTP
  // falla, el alta se completa igual. Sin este botón, el usuario se
  // quedaba sin cuenta usable y sin salida (volver a registrarse da
  // 409 "email ya registrado").
  const resend = async () => {
    if (!email) return
    setError('')
    setSending(true)
    try {
      await authApi.resendVerification(email)
      setResent(true)
    } catch (err: unknown) {
      setError(getErrorMessage(
        err,
        'No se pudo reenviar el correo. Prueba de nuevo en unos minutos.',
      ))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-obsidian-900 via-obsidian-800
      to-obsidian-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl p-10 max-w-md w-full
        text-center">
        <div className="inline-flex items-center justify-center
          bg-gradient-to-br from-gold-400 to-gold-600 rounded-2xl p-3.5 mb-6
          shadow-gold">
          <EyeOfHorus className="h-9 w-12 text-obsidian-900" strokeWidth={6} />
        </div>

        <MailCheck className="h-14 w-14 text-lapis-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Revisa tu correo
        </h2>
        <p className="text-gray-500 mb-2">
          Te enviamos un enlace de verificación
          {email ? <> a <strong className="text-gray-700">{email}</strong></> : null}.
          Haz clic en él para activar tu cuenta.
        </p>
        <p className="text-gray-400 text-sm mb-6">
          ¿No lo ves? Revisa tu carpeta de spam. El enlace puede tardar
          un par de minutos en llegar.
        </p>

        {error && (
          <div role="alert" className="bg-red-50 border border-red-200
            text-red-700 text-sm rounded-xl px-4 py-3 mb-4 text-left">
            {error}
          </div>
        )}

        <Link to="/login" className="btn-primary w-full inline-block py-3">
          Ya verifiqué, iniciar sesión
        </Link>

        {email && (
          resent ? (
            <p className="text-sm text-green-600 mt-4">
              Listo, te reenviamos el enlace. Revisa tu bandeja.
            </p>
          ) : (
            <button onClick={resend} disabled={sending}
              className="mt-4 w-full inline-flex items-center justify-center
                gap-2 text-sm text-obsidian-700 font-semibold
                hover:underline disabled:opacity-60">
              {sending
                ? <Spinner size="sm" />
                : <RefreshCw className="h-4 w-4" />
              }
              {sending ? 'Reenviando...' : 'Reenviar el correo'}
            </button>
          )
        )}

        <p className="text-center text-sm text-gray-400 mt-4">
          ¿Correo equivocado?{' '}
          <Link to="/register"
            className="text-obsidian-700 font-semibold hover:underline">
            Registrarse de nuevo
          </Link>
        </p>
      </div>
    </div>
  )
}
