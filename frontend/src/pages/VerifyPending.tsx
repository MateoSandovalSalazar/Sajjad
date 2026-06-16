import { Link, useSearchParams } from 'react-router-dom'
import { MailCheck } from 'lucide-react'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'

export function VerifyPending() {
  const [params] = useSearchParams()
  const email = params.get('email')

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

        <Link to="/login" className="btn-primary w-full inline-block py-3">
          Ya verifiqué, iniciar sesión
        </Link>

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
