import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Node 26 define su propio `localStorage` global (experimental, y
// deshabilitado sin --localstorage-file), que gana al de jsdom: dentro
// de los tests `localStorage` quedaba en undefined y cualquier test
// que tocara la sesión reventaba con "Cannot read properties of
// undefined". El código de producción lo usa en todas partes
// (api/client.ts, store/auth.ts), así que aquí se pone uno en memoria.
class MemoryStorage implements Storage {
  private data = new Map<string, string>()

  get length() { return this.data.size }
  clear() { this.data.clear() }
  getItem(key: string) { return this.data.get(key) ?? null }
  key(index: number) { return [...this.data.keys()][index] ?? null }
  removeItem(key: string) { this.data.delete(key) }
  setItem(key: string, value: string) {
    this.data.set(key, String(value))
  }
}

function installStorage(name: 'localStorage' | 'sessionStorage') {
  const existing = (globalThis as Record<string, unknown>)[name]
  if (existing) return
  const storage = new MemoryStorage()
  for (const target of [globalThis, window]) {
    Object.defineProperty(target, name, {
      value: storage,
      writable: false,
      configurable: true,
    })
  }
}

installStorage('localStorage')
installStorage('sessionStorage')

// jsdom no implementa matchMedia, y algún componente de Tailwind o
// de recharts lo consulta al montar.
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}

afterEach(() => {
  cleanup()
  localStorage.clear()
})
