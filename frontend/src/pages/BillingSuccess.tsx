import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2 } from 'lucide-react'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

// Página de retorno tras el checkout de Mercado Pago (back_url).
// La activación real del plan ocurre vía webhook en el backend; aquí
// solo confirmamos e invalidamos la caché para reflejar el nuevo plan.
export function BillingSuccess() {
  useDocumentTitle('Pago recibido')
  const qc = useQueryClient()

  useEffect(() => {
    qc.invalidateQueries({ queryKey: ['subscription'] })
  }, [qc])

  return (
    <div className="max-w-lg mx-auto text-center py-16">
      <div className="inline-flex items-center justify-center w-16 h-16
        bg-green-50 rounded-2xl mb-5">
        <CheckCircle2 className="h-9 w-9 text-green-500" />
      </div>
      <h1 className="text-2xl font-black text-gray-900 mb-2">
        ¡Gracias por tu pago!
      </h1>
      <p className="text-gray-500 mb-2">
        Estamos confirmando tu suscripción con Mercado Pago. La activación
        puede tardar unos minutos.
      </p>
      <p className="text-sm text-gray-400 mb-8">
        Recibirás un correo cuando tu plan esté activo. Puedes seguir usando
        Sajjad mientras tanto.
      </p>
      <div className="flex items-center justify-center gap-3">
        <Link to="/dashboard" className="btn-primary">
          Ir al panel
        </Link>
        <Link to="/account" className="btn-secondary">
          Ver mi plan
        </Link>
      </div>
    </div>
  )
}
