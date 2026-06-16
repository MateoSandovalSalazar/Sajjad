/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Obsidiana — fondos profundos casi negros con matiz cálido/verde,
        // como la piedra volcánica pulida del antiguo Egipto.
        obsidian: {
          50:  '#eef2f1',
          100: '#d6e0dd',
          200: '#aebfba',
          500: '#2b3d3a',
          600: '#1f2d2b',
          700: '#17211f',
          800: '#101817',
          900: '#0a0f0e',
          950: '#060908',
        },
        // Oro faraónico — el acento de la marca. Premium, vigilante, sagrado.
        gold: {
          50:  '#fbf6e7',
          100: '#f6ecc6',
          200: '#efdc93',
          300: '#e6cb66',
          400: '#dab94e',
          500: '#c9a227',  // primario
          600: '#a8851d',
          700: '#856819',
          800: '#5f4a13',
        },
        // Lapislázuli — azul profundo egipcio (la máscara de Tutankamón).
        // Secundario para gradientes y paneles.
        lapis: {
          400: '#3f6fc4',
          500: '#2a51a3',
          600: '#1f3f85',
          700: '#172f66',
          800: '#101f45',
          900: '#0a1530',
        },
        // Arena / papiro — superficies claras cálidas en vez de gris frío.
        sand: {
          50:  '#faf7f0',
          100: '#f3ece0',
          200: '#e8dcc6',
          300: '#d9c8a8',
        },
        risk: {
          critical: '#dc2626',
          high:     '#ea580c',
          medium:   '#d97706',
          low:      '#2563eb',
          safe:     '#16a34a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'gold': '0 10px 40px -10px rgba(201, 162, 39, 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow':  'spin 2s linear infinite',
        'float':      'float 6s ease-in-out infinite',
        'eye-glow':   'eyeGlow 4s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-12px)' },
        },
        eyeGlow: {
          '0%, 100%': { opacity: '0.4', filter: 'drop-shadow(0 0 8px rgba(201,162,39,0.3))' },
          '50%':      { opacity: '1', filter: 'drop-shadow(0 0 24px rgba(201,162,39,0.6))' },
        },
        slideIn: {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
