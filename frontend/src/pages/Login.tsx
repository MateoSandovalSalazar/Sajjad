import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../lib/errors'
import { useAuthStore } from '../store/auth'
import { Spinner } from '../components/ui/Spinner'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'

export function Login() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPwd, setShowPwd]   = useState(false)
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const { setAuth }             = useAuthStore()
  const navigate                = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await authApi.login(email, password)
      // El backend exige email verificado en los endpoints protegidos.
      // Si aún no lo está, no llamamos a /me (devolvería 403); mandamos
      // al usuario a la pantalla de "revisa tu correo".
      if (!data.is_verified) {
        navigate(`/verify-pending?email=${encodeURIComponent(email)}`)
        return
      }
      // Guardamos los tokens ANTES de pedir el perfil: el interceptor de
      // axios adjunta el access token desde localStorage, así que /users/me
      // fallaría con 401 si lo llamáramos antes de guardarlo.
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      const me = await authApi.me()
      setAuth(me.data, data.access_token, data.refresh_token)
      navigate('/dashboard')
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Email o contraseña incorrectos.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-obsidian-900 via-obsidian-800
      to-obsidian-700 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center
            bg-gradient-to-br from-gold-400 to-gold-600 rounded-2xl p-3.5 mb-4
            shadow-gold">
            <EyeOfHorus className="h-9 w-12 text-obsidian-900" strokeWidth={6} />
          </div>
          <h1 className="text-white font-black text-3xl tracking-tight">
            SAJJAD<span className="text-gold-400">.</span>
          </h1>
          <p className="text-white/60 text-sm mt-1">
            Monitor de Seguridad Empresarial
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-3xl shadow-2xl p-8">
          <h2 className="text-gray-900 font-bold text-xl mb-1">
            Bienvenido de regreso
          </h2>
          <p className="text-gray-500 text-sm mb-6">
            Ingresa para ver el estado de seguridad de tu empresa.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700
              text-sm rounded-xl px-4 py-3 mb-4">
              {error}
            </div>
          )}

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Correo electrónico
              </label>
              <input type="email" required value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="tu@empresa.com"
                className="input" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <input type={showPwd ? 'text' : 'password'} required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input pr-11" />
                <button type="button"
                  onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2
                    text-gray-400 hover:text-gray-600">
                  {showPwd
                    ? <EyeOff className="h-5 w-5" />
                    : <Eye className="h-5 w-5" />
                  }
                </button>
              </div>
            </div>

            <div className="text-right">
              <Link to="/forgot-password"
                className="text-sm text-obsidian-600 hover:text-obsidian-800
                  hover:underline">
                ¿Olvidaste tu contraseña?
              </Link>
            </div>

            <button type="submit" disabled={loading}
              className="btn-primary w-full flex items-center justify-center
                gap-2 py-3">
              {loading ? <Spinner size="sm" /> : null}
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            ¿No tienes cuenta?{' '}
            <Link to="/register"
              className="text-obsidian-700 font-semibold hover:underline">
              Crear cuenta gratis
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
