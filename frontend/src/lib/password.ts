// Comprobación de contraseña del lado del cliente.
//
// La fuente de verdad es `backend/app/core/passwords.py`: él rechaza
// además contraseñas repetitivas y las que aparecen en filtraciones
// conocidas, y su mensaje (en español) se muestra tal cual si llega un
// 422. Esto es sólo para no hacer un viaje al servidor por errores
// evidentes mientras el usuario escribe.
//
// Mantener en el mínimo imprescindible: duplicar aquí la política
// entera garantiza que las dos versiones se desincronicen.

export function checkPassword(value: string): string | null {
  if (value.length < 8) {
    return 'La contraseña debe tener al menos 8 caracteres.'
  }
  if (!/[A-Z]/.test(value)) {
    return 'La contraseña debe incluir al menos una mayúscula.'
  }
  if (!/[a-z]/.test(value)) {
    return 'La contraseña debe incluir al menos una minúscula.'
  }
  if (!/[0-9]/.test(value)) {
    return 'La contraseña debe incluir al menos un número.'
  }
  return null
}
