import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MailCheck } from 'lucide-react'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../lib/errors'
import { Spinner } from '../components/ui/Spinner'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

export function ForgotPassword() {
  useDocumentTitle('Recuperar contraseña')

  const [email, setEmail]     = useState('')
  const [sent, setSent]       = useState(false)
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.forgotPassword(email)
      // El backend responde 202 tanto si el correo existe como si no,
      // para no revelar qué direcciones están registradas. La pantalla
      // dice lo mismo en los dos casos, a propósito.
      setSent(true)
    } catch (err: unknown) {
      setError(getErrorMessage(
        err,
        'No se pudo enviar el correo. Intenta de nuevo en unos minutos.',
      ))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-obsidian-900 via-obsidian-800
      to-obsidian-700 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center
            bg-gradient-to-br from-gold-400 to-gold-600 rounded-2xl p-3.5 mb-4
            shadow-gold">
            <EyeOfHorus className="h-9 w-12 text-obsidian-900" strokeWidth={6} />
          </div>
          <h1 className="text-white font-black text-3xl tracking-tight">
            SAJJAD<span className="text-gold-400">.</span>
          </h1>
        </div>

        <div className="bg-white rounded-3xl shadow-2xl p-8">
          {sent ? (
            <div className="text-center">
              <div className="inline-flex items-center justify-center
                bg-green-50 rounded-2xl p-3 mb-4">
                <MailCheck className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-gray-900 font-bold text-xl mb-2">
                Revisa tu correo
              </h2>
              <p className="text-gray-500 text-sm mb-6">
                Si <strong className="text-gray-700">{email}</strong> está
                registrado, te enviamos un enlace para restablecer la
                contraseña. El enlace caduca en una hora.
              </p>
              <Link to="/login" className="btn-primary inline-block px-6 py-3">
                Volver a iniciar sesión
              </Link>
            </div>
          ) : (
            <>
              <h2 className="text-gray-900 font-bold text-xl mb-1">
                Recuperar contraseña
              </h2>
              <p className="text-gray-500 text-sm mb-6">
                Escribe tu correo y te enviamos un enlace para crear una
                contraseña nueva.
              </p>

              {error && (
                <div role="alert" className="bg-red-50 border
                  border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 mb-4">
                  {error}
                </div>
              )}

              <form onSubmit={submit} className="space-y-4">
                <div>
                  <label htmlFor="forgot-email"
                    className="block text-sm font-medium text-gray-700 mb-1.5">
                    Correo electrónico
                  </label>
                  <input id="forgot-email" type="email" required value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="tu@empresa.com"
                    className="input" />
                </div>

                <button type="submit" disabled={loading}
                  className="btn-primary w-full flex items-center justify-center
                    gap-2 py-3">
                  {loading ? <Spinner size="sm" /> : null}
                  {loading ? 'Enviando...' : 'Enviar enlace'}
                </button>
              </form>

              <p className="text-center text-sm text-gray-500 mt-6">
                <Link to="/login"
                  className="text-obsidian-700 font-semibold hover:underline">
                  Volver a iniciar sesión
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
