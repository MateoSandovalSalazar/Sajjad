import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Globe, ShieldCheck, AlertTriangle, Trash2, ChevronRight } from 'lucide-react'
import { domainsApi } from '../api/domains'
import { getErrorMessage } from '../lib/errors'
import { toast } from '../store/toast'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { Spinner } from '../components/ui/Spinner'
import type { Domain } from '../types'

function AddDomainForm({ onClose }: { onClose: () => void }) {
  const [fqdn, setFqdn] = useState('')
  const [authorized, setAuthorized] = useState(false)
  const [error, setError] = useState('')
  const qc = useQueryClient()

  const add = useMutation({
    mutationFn: () =>
      domainsApi
        .create(fqdn.trim().toLowerCase(), authorized)
        .then(r => r.data),
    onSuccess: (created) => {
      // El POST devuelve el dominio creado (autoritativo). Lo insertamos
      // directo en la caché en vez de invalidar: el backend a veces no
      // refleja el escritura en una lectura inmediata (envía la respuesta
      // antes de que el commit sea visible), y un refetch perdería la
      // carrera y mostraría la lista sin el dominio nuevo.
      qc.setQueryData<Domain[]>(['domains'], (old) =>
        old ? [...old, created] : [created])
      toast.success('Dominio agregado. Ahora verifícalo.')
      onClose()
    },
    onError: (err: unknown) => {
      setError(getErrorMessage(err, 'No se pudo agregar el dominio.'))
    },
  })

  return (
    <div className="card p-6 mb-6 border-2 border-obsidian-700/20">
      <h3 className="font-bold text-gray-900 mb-4">Agregar nuevo dominio</h3>
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm
          rounded-xl px-4 py-3 mb-4">
          {error}
        </div>
      )}
      <div className="flex gap-3">
        <input value={fqdn} onChange={e => setFqdn(e.target.value)}
          placeholder="empresa.com"
          className="input flex-1"
          onKeyDown={e =>
            e.key === 'Enter' && fqdn && authorized && add.mutate()}
        />
        <button onClick={() => add.mutate()}
          disabled={!fqdn || !authorized || add.isPending}
          className="btn-primary flex items-center gap-2">
          {add.isPending ? <Spinner size="sm" /> : <Plus className="h-4 w-4" />}
          Agregar
        </button>
        <button onClick={onClose} className="btn-secondary">Cancelar</button>
      </div>

      {/* Declaración de propiedad. No es un trámite: es la base legal
          que respalda cada escaneo, y queda registrada con fecha e IP. */}
      <label className="flex items-start gap-2.5 mt-4 cursor-pointer
        rounded-xl border border-gold-500/30 bg-gold-50/40 px-4 py-3">
        <input type="checkbox" checked={authorized}
          onChange={e => setAuthorized(e.target.checked)}
          className="mt-0.5 h-4 w-4 shrink-0 accent-gold-600" />
        <span className="text-sm text-gray-700">
          Declaro que soy el propietario de este dominio, o que cuento
          con autorización expresa por escrito de su propietario, para
          que Sajjad analice su infraestructura expuesta. Entiendo que
          esta declaración queda registrada.
        </span>
      </label>
      <p className="text-xs text-gray-400 mt-2">
        Solo el dominio raíz, sin https:// — ej: <code>empresa.com</code>
      </p>
    </div>
  )
}

export function Domains() {
  useDocumentTitle('Mis dominios')
  const [showForm, setShowForm] = useState(false)
  const qc = useQueryClient()

  const { data: domains, isLoading } = useQuery({
    queryKey: ['domains'],
    queryFn: () => domainsApi.list().then(r => r.data),
  })

  const remove = useMutation({
    mutationFn: (id: string) => domainsApi.delete(id),
    onSuccess: (_data, id) => {
      // Quitamos de la caché directamente (misma razón que en el alta:
      // un refetch inmediato podría aún ver el dominio borrado).
      qc.setQueryData<Domain[]>(['domains'], (old) =>
        old ? old.filter(d => d.id !== id) : old)
      toast.success('Dominio eliminado.')
    },
    onError: () => toast.error('No se pudo eliminar el dominio.'),
  })

  if (isLoading) return (
    <div className="flex items-center justify-center h-64"><Spinner size="lg" /></div>
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-black text-gray-900">Mis dominios</h1>
          <p className="text-gray-500 mt-1">
            Administra los dominios que Sajjad monitorea.
          </p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Agregar dominio
        </button>
      </div>

      {showForm && <AddDomainForm onClose={() => setShowForm(false)} />}

      {!domains?.length && !showForm ? (
        <div className="card p-16 text-center">
          <Globe className="h-12 w-12 text-gray-200 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Sin dominios aún
          </h2>
          <p className="text-gray-500 mb-6">
            Agrega el dominio de tu empresa para comenzar el monitoreo.
          </p>
          <button onClick={() => setShowForm(true)}
            className="btn-primary inline-flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Agregar mi primer dominio
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {domains?.map(domain => (
            <div key={domain.id}
              className="card px-5 py-4 flex items-center gap-4 group">
              {domain.is_verified
                ? <ShieldCheck className="h-5 w-5 text-green-500 shrink-0" />
                : <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />
              }
              <div className="flex-1 min-w-0">
                <p className="font-bold text-gray-900 truncate">{domain.fqdn}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {domain.is_verified
                    ? `Verificado el ${new Date(domain.verified_at!).toLocaleDateString('es-MX')}`
                    : 'Pendiente de verificación DNS'}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Link to={`/domains/${domain.id}`}
                  className="btn-secondary flex items-center gap-1.5 text-sm py-1.5 px-3">
                  {domain.is_verified ? 'Ver seguridad' : 'Verificar'}
                  <ChevronRight className="h-3.5 w-3.5" />
                </Link>
                <button
                  onClick={() => {
                    if (confirm(`¿Eliminar ${domain.fqdn}? Se borrarán todos los scans.`))
                      remove.mutate(domain.id)
                  }}
                  className="p-2 text-gray-300 hover:text-red-500 transition-colors">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
