import { CheckCircle, XCircle, Info, X } from 'lucide-react'
import { useToastStore, type ToastKind } from '../../store/toast'

const KIND_STYLES: Record<ToastKind, { bar: string; icon: typeof Info }> = {
  success: { bar: 'border-l-green-500', icon: CheckCircle },
  error:   { bar: 'border-l-red-500',   icon: XCircle },
  info:    { bar: 'border-l-lapis-500', icon: Info },
}

const ICON_COLOR: Record<ToastKind, string> = {
  success: 'text-green-500',
  error:   'text-red-500',
  info:    'text-lapis-500',
}

export function Toaster() {
  const { toasts, dismiss } = useToastStore()

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2
      w-[calc(100vw-2rem)] max-w-sm pointer-events-none">
      {toasts.map((t) => {
        const Icon = KIND_STYLES[t.kind].icon
        return (
          <div key={t.id}
            className={`pointer-events-auto flex items-start gap-3 bg-white
              rounded-xl shadow-lg border border-gray-100 border-l-4
              ${KIND_STYLES[t.kind].bar} px-4 py-3
              animate-[slideIn_0.2s_ease-out]`}>
            <Icon className={`h-5 w-5 shrink-0 mt-0.5 ${ICON_COLOR[t.kind]}`} />
            <p className="flex-1 text-sm text-gray-700">{t.message}</p>
            <button onClick={() => dismiss(t.id)}
              className="text-gray-300 hover:text-gray-600 transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
