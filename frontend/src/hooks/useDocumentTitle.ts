import { useEffect } from 'react'

// Fija el <title> del documento por página y lo restaura al desmontar.
// Detalle de profesionalismo: pestañas del navegador con contexto claro.
export function useDocumentTitle(title: string) {
  useEffect(() => {
    const previous = document.title
    document.title = `${title} · Sajjad`
    return () => {
      document.title = previous
    }
  }, [title])
}
