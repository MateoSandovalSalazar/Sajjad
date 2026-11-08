import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, ShieldAlert } from 'lucide-react'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../lib/errors'
import { checkPassword } from '../lib/password'
import { Spinner } from '../components/ui/Spinner'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { toast } from '../store/toast'

export function ResetPassword() {
  useDocumentTitle('Nueva contraseña')

  const [params]  = useSearchParams()
  const token     = params.get('token') ?? ''
  const navigate  = useNavigate()

  const [password, setPassword] = useState('')
  const [confirm, setConfirm]   = useState('')
  const [showPwd, setShowPwd]   = useState(false)
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('Las contraseñas no coinciden.')
      return
    }
    const weak = checkPassword(password)
    if (weak) {
      setError(weak)
      return
    }

    setLoading(true)
    try {
      await authApi.resetPassword(token, password)
      // Restablecer la contraseña invalida las sesiones abiertas en el
      // backend (sube token_version), así que cualquier token guardado
      // en este navegador ya no sirve: lo limpiamos antes de salir.
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      toast.success('Contraseña actualizada. Ya puedes iniciar sesión.')
      navigate('/login')
    } catch (err: unknown) {
      setError(getErrorMessage(
        err,
        'No se pudo cambiar la contraseña. El enlace pudo caducar.',
      ))
    } finally {
      setLoading(false)
    }
  }

  const shell = (children: React.ReactNode) => (
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
        <div className="bg-white rounded-3xl shadow-2xl p-8">{children}</div>
      </div>
    </div>
  )

  // Enlace abierto a mano o recortado por el cliente de correo.
  if (!token) {
    return shell(
      <div className="text-center">
        <div className="inline-flex items-center justify-center
          bg-red-50 rounded-2xl p-3 mb-4">
          <ShieldAlert className="h-8 w-8 text-red-600" />
        </div>
        <h2 className="text-gray-900 font-bold text-xl mb-2">
          Enlace inválido
        </h2>
        <p className="text-gray-500 text-sm mb-6">
          Este enlace no trae el código de verificación. Pide uno nuevo
          desde la pantalla de recuperación.
        </p>
        <Link to="/forgot-password"
          className="btn-primary inline-block px-6 py-3">
          Pedir otro enlace
        </Link>
      </div>,
    )
  }

  return shell(
    <>
      <h2 className="text-gray-900 font-bold text-xl mb-1">
        Nueva contraseña
      </h2>
      <p className="text-gray-500 text-sm mb-6">
        Elige una contraseña nueva. Al guardarla se cerrarán las demás
        sesiones de tu cuenta.
      </p>

      {error && (
        <div role="alert" className="bg-red-50 border border-red-200
          text-red-700 text-sm rounded-xl px-4 py-3 mb-4">
          {error}
        </div>
      )}

      <form onSubmit={submit} className="space-y-4">
        <div>
          <label htmlFor="new-password"
            className="block text-sm font-medium text-gray-700 mb-1.5">
            Nueva contraseña
          </label>
          <div className="relative">
            <input id="new-password"
              type={showPwd ? 'text' : 'password'} required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="input pr-11" />
            <button type="button"
              onClick={() => setShowPwd(!showPwd)}
              aria-label={showPwd ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              className="absolute right-3 top-1/2 -translate-y-1/2
                text-gray-400 hover:text-gray-600">
              {showPwd
                ? <EyeOff className="h-5 w-5" />
                : <Eye className="h-5 w-5" />
              }
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1.5">
            Mínimo 8 caracteres, con mayúscula, minúscula y número.
          </p>
        </div>

        <div>
          <label htmlFor="confirm-password"
            className="block text-sm font-medium text-gray-700 mb-1.5">
            Repetir contraseña
          </label>
          <input id="confirm-password"
            type={showPwd ? 'text' : 'password'} required
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
            placeholder="••••••••"
            className="input" />
        </div>

        <button type="submit" disabled={loading}
          className="btn-primary w-full flex items-center justify-center
            gap-2 py-3">
          {loading ? <Spinner size="sm" /> : null}
          {loading ? 'Guardando...' : 'Guardar contraseña'}
        </button>
      </form>

      <p className="text-center text-sm text-gray-500 mt-6">
        <Link to="/login"
          className="text-obsidian-700 font-semibold hover:underline">
          Volver a iniciar sesión
        </Link>
      </p>
    </>,
  )
}
