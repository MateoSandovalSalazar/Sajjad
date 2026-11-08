import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import { getErrorMessage } from '../lib/errors'
import { Spinner } from '../components/ui/Spinner'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'

export function Register() {
  const [form, setForm]     = useState({
    full_name: '', company: '', email: '', password: '', confirm: ''
  })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)
  const navigate            = useNavigate()

  const set = (k: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) {
      setError('Las contraseñas no coinciden.')
      return
    }
    if (form.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.')
      return
    }
    if (!/[A-Z]/.test(form.password)) {
      setError('La contraseña debe contener al menos una letra mayúscula.')
      return
    }
    if (!/[0-9]/.test(form.password)) {
      setError('La contraseña debe contener al menos un número.')
      return
    }
    setLoading(true)
    try {
      await authApi.register({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        company: form.company || undefined,
      })
      // El backend requiere verificación de email antes de habilitar el
      // acceso, así que mandamos al usuario a revisar su correo en vez
      // de intentar entrar directo (fallaría con 403).
      navigate(`/verify-pending?email=${encodeURIComponent(form.email)}`)
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Error al crear la cuenta. Intenta de nuevo.'))
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
          <h2 className="text-gray-900 font-bold text-xl mb-1">
            Crear cuenta
          </h2>
          <p className="text-gray-500 text-sm mb-6">
            Empieza a monitorear la seguridad de tu empresa.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700
              text-sm rounded-xl px-4 py-3 mb-4">
              {error}
            </div>
          )}

          <form onSubmit={submit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Nombre completo
                </label>
                <input type="text" required value={form.full_name}
                  onChange={set('full_name')} placeholder="Ana García"
                  className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Empresa <span className="text-gray-400">(opcional)</span>
                </label>
                <input type="text" value={form.company}
                  onChange={set('company')} placeholder="Mi empresa"
                  className="input" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Correo electrónico
              </label>
              <input type="email" required value={form.email}
                onChange={set('email')} placeholder="tu@empresa.com"
                className="input" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Contraseña
              </label>
              <input type="password" required value={form.password}
                onChange={set('password')} placeholder="Mínimo 8 caracteres"
                className="input" />
              <p className="text-xs text-gray-400 mt-1">
                Mínimo 8 caracteres, una mayúscula y un número.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Confirmar contraseña
              </label>
              <input type="password" required value={form.confirm}
                onChange={set('confirm')} placeholder="••••••••"
                className="input" />
            </div>

            <button type="submit" disabled={loading}
              className="btn-primary w-full flex items-center justify-center
                gap-2 py-3">
              {loading ? <Spinner size="sm" /> : null}
              {loading ? 'Creando cuenta...' : 'Crear cuenta gratis'}
            </button>

            <p className="text-center text-xs text-gray-400 mt-4">
              Al crear la cuenta aceptas los{' '}
              <Link to="/legal/terminos"
                className="text-obsidian-700 hover:underline">
                Términos de Servicio
              </Link>
              {' '}y la{' '}
              <Link to="/legal/privacidad"
                className="text-obsidian-700 hover:underline">
                Política de Privacidad
              </Link>
              .
            </p>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            ¿Ya tienes cuenta?{' '}
            <Link to="/login"
              className="text-obsidian-700 font-semibold hover:underline">
              Ingresar
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
