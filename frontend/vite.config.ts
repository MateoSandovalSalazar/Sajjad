// defineConfig se importa de vitest/config, no de vite: es el que
// conoce la clave `test`. Con el de vite, tsc no la acepta.
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Sin esto, vitest intentaría ejecutar los tests de Playwright
    // (que necesitan un navegador y un servidor levantado).
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
