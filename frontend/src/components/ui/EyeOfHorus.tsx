/**
 * Ojo de Horus (Wadjet) — el símbolo de protección y vigilancia
 * del antiguo Egipto. Es la identidad de Sajjad: "el que vigila
 * en constante atención".
 *
 * Line-art con currentColor para poder teñirlo (oro sobre obsidiana).
 * Construido con trazos para que escale nítido desde favicon (16px)
 * hasta hero (200px+).
 */
interface Props {
  className?: string
  strokeWidth?: number
}

export function EyeOfHorus({ className = '', strokeWidth = 5 }: Props) {
  return (
    <svg
      viewBox="0 0 112 80"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {/* Ceja */}
      <path d="M12 22 C38 6 74 4 102 16" />
      {/* Párpado superior */}
      <path d="M8 38 C30 20 66 20 94 34" />
      {/* Párpado inferior */}
      <path d="M9 39 C30 56 62 58 88 43" />
      {/* Iris / pupila */}
      <circle cx="46" cy="38" r="8.5" fill="currentColor" stroke="none" />
      {/* Lágrima recta (descendente) */}
      <path d="M40 53 L33 76" />
      {/* Espiral / rizo característico */}
      <path d="M50 54 C56 70 47 78 38 73" />
      {/* Cola desde la comisura externa */}
      <path d="M88 43 L108 50" />
    </svg>
  )
}

/**
 * Logo completo de Sajjad: ojo dorado en chip + wordmark.
 * `variant` controla el color del texto según el fondo.
 */
export function SajjadLogo({
  variant = 'light',
  size = 'md',
}: {
  variant?: 'light' | 'dark'
  size?: 'sm' | 'md' | 'lg'
}) {
  const chip = {
    sm: 'h-7 w-7 p-1',
    md: 'h-9 w-9 p-1.5',
    lg: 'h-11 w-11 p-2',
  }[size]
  const text = {
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl',
  }[size]
  const textColor = variant === 'light' ? 'text-white' : 'text-obsidian-900'

  return (
    <span className="flex items-center gap-2.5">
      <span className={`${chip} rounded-lg bg-gradient-to-br from-gold-400
        to-gold-600 flex items-center justify-center shadow-gold`}>
        <EyeOfHorus className="text-obsidian-900 w-full h-full" strokeWidth={6} />
      </span>
      <span className={`${textColor} font-black ${text} tracking-tight`}>
        SAJJAD<span className="text-gold-500">.</span>
      </span>
    </span>
  )
}
