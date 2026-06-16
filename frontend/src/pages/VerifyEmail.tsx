import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { CheckCircle, XCircle } from 'lucide-react'
import { authApi } from '../api/auth'
import { Spinner } from '../components/ui/Spinner'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'

export function VerifyEmail() {
  const [params] = useSearchParams()
  const navigate  = useNavigate()
  const token     = params.get('token')

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  useEffect(() => {
    if (!token) { setStatus('error'); return }
    authApi.verifyEmail(token)
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'))
  }, [token])

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

        {status === 'loading' && (
          <>
            <div className="flex justify-center mb-4">
              <Spinner size="lg" />
            </div>
            <p className="text-gray-500">Verificando tu correo...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="h-14 w-14 text-green-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              ¡Correo verificado!
            </h2>
            <p className="text-gray-500 mb-6">
              Tu cuenta está activa. Ya puedes iniciar sesión y comenzar
              a monitorear tu empresa.
            </p>
            <button onClick={() => navigate('/login')}
              className="btn-primary w-full py-3">
              Ir al login
            </button>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="h-14 w-14 text-red-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Enlace inválido
            </h2>
            <p className="text-gray-500 mb-6">
              El enlace de verificación es inválido o ya expiró.
              Intenta registrarte de nuevo.
            </p>
            <button onClick={() => navigate('/register')}
              className="btn-primary w-full py-3">
              Volver al registro
            </button>
          </>
        )}
      </div>
    </div>
  )
}
