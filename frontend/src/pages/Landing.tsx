import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Globe, Lock, Mail, AlertTriangle, Search,
  ChevronRight, Check, Zap, Eye, FileText, Server,
  Key, Menu, X,
} from 'lucide-react'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'

function Nav() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen]         = useState(false)

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 24)
    window.addEventListener('scroll', fn)
    return () => window.removeEventListener('scroll', fn)
  }, [])

  return (
    <nav className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
      scrolled
        ? 'bg-obsidian-900/95 backdrop-blur shadow-xl'
        : 'bg-transparent'
    }`}>
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5">
          <div className="h-8 w-8 p-1 rounded-lg bg-gradient-to-br
            from-gold-400 to-gold-600 flex items-center justify-center shadow-gold">
            <EyeOfHorus className="text-obsidian-900 w-full h-full" strokeWidth={6} />
          </div>
          <span className="text-white font-black text-xl tracking-tight">
            SAJJAD<span className="text-gold-500">.</span>
          </span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8">
          {[
            { label: 'Características', href: '#features' },
            { label: 'Cómo funciona', href: '#how' },
            { label: 'Precios', href: '#pricing' },
          ].map(({ label, href }) => (
            <a key={href} href={href}
              className="text-white/70 hover:text-white text-sm font-medium
                transition-colors">
              {label}
            </a>
          ))}
        </div>

        {/* CTAs */}
        <div className="hidden md:flex items-center gap-3">
          <Link to="/login"
            className="text-white/80 hover:text-white text-sm font-medium
              transition-colors px-4 py-2">
            Iniciar sesión
          </Link>
          <Link to="/register"
            className="bg-gold-500 hover:bg-gold-400 text-obsidian-900 font-semibold
              text-sm px-5 py-2 rounded-lg transition-colors">
            Empezar gratis
          </Link>
        </div>

        {/* Mobile toggle */}
        <button onClick={() => setOpen(!open)}
          className="md:hidden text-white/80 hover:text-white">
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-obsidian-900 border-t border-white/10 px-6 py-4 space-y-4">
          {['#features', '#how', '#pricing'].map(href => (
            <a key={href} href={href} onClick={() => setOpen(false)}
              className="block text-white/70 hover:text-white text-sm font-medium py-1">
              {href === '#features' ? 'Características'
                : href === '#how' ? 'Cómo funciona' : 'Precios'}
            </a>
          ))}
          <div className="pt-2 border-t border-white/10 flex flex-col gap-2">
            <Link to="/login" className="btn-secondary py-2 text-center text-sm">
              Iniciar sesión
            </Link>
            <Link to="/register"
              className="bg-gold-500 hover:bg-gold-400 text-obsidian-900 font-semibold
                text-sm px-5 py-2.5 rounded-lg text-center transition-colors">
              Empezar gratis
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}

function Hero() {
  return (
    <section className="relative min-h-screen overflow-hidden bg-gradient-to-br
      from-obsidian-950 via-lapis-900 to-obsidian-900 flex items-center
      justify-center px-6 pt-16">
      {/* Ojo de Horus gigante de fondo */}
      <EyeOfHorus
        className="absolute -right-20 top-1/4 w-[680px] text-gold-500/10
          pointer-events-none select-none animate-eye-glow"
        strokeWidth={2}
      />
      {/* Resplandor dorado superior */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px]
        bg-gold-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative z-10 max-w-4xl mx-auto text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20
          rounded-full px-4 py-1.5 mb-8">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-white/80 text-sm font-medium">
            Monitoreo continuo 24/7
          </span>
        </div>

        <h1 className="text-5xl md:text-6xl lg:text-7xl font-black text-white
          leading-tight tracking-tight mb-6">
          Sabe exactamente qué tiene{' '}
          <span className="text-gold-400">expuesto</span>{' '}
          tu empresa
        </h1>

        <p className="text-white/60 text-xl md:text-2xl leading-relaxed max-w-2xl
          mx-auto mb-10">
          Sajjad escanea tu superficie de ataque externa y te dice qué corregir
          antes de que lo encuentre un atacante.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/register"
            className="inline-flex items-center gap-2 bg-gold-500
              hover:bg-gold-400 text-obsidian-900 font-bold text-lg px-8 py-4
              rounded-xl transition-all hover:scale-105 shadow-lg
              shadow-gold-500/25">
            Empezar gratis
            <ChevronRight className="h-5 w-5" />
          </Link>
          <a href="#how"
            className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/15
              text-white font-semibold text-lg px-8 py-4 rounded-xl
              transition-all border border-white/20">
            Ver cómo funciona
          </a>
        </div>

        {/* Social proof */}
        <p className="text-white/30 text-sm mt-10">
          Sin tarjeta de crédito · Primer dominio gratis · Reporte en minutos
        </p>

        {/* Floating stats */}
        <div className="mt-20 grid grid-cols-3 gap-4 max-w-xl mx-auto">
          {[
            { value: '9', label: 'Etapas de análisis' },
            { value: '40+', label: 'Fuentes OSINT' },
            { value: '100', label: 'Risk Score transparente' },
          ].map(({ value, label }) => (
            <div key={label}
              className="bg-white/5 border border-white/10 rounded-2xl px-4 py-5">
              <p className="text-3xl font-black text-gold-400">{value}</p>
              <p className="text-white/50 text-xs mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const FEATURES = [
  {
    icon: Globe,
    title: 'Subdominios expuestos',
    desc: 'Descubre todos los subdominios olvidados que apuntan a servicios activos o vulnerables.',
  },
  {
    icon: Server,
    title: 'Puertos y servicios',
    desc: 'Detecta bases de datos, RDP o VNC expuestos directamente a internet sin protección.',
  },
  {
    icon: Lock,
    title: 'Certificados TLS',
    desc: 'Alerta de certificados vencidos o por vencer antes de que afecten a tus clientes.',
  },
  {
    icon: Mail,
    title: 'Seguridad de email',
    desc: 'Verifica SPF, DKIM y DMARC para proteger tu dominio del email spoofing.',
  },
  {
    icon: Key,
    title: 'Credenciales filtradas',
    desc: 'Busca en bases de datos de brechas si algún correo corporativo fue comprometido.',
  },
  {
    icon: AlertTriangle,
    title: 'Vulnerabilidades conocidas',
    desc: 'Detecta CVEs activos, paneles admin expuestos y configuraciones por defecto.',
  },
  {
    icon: Search,
    title: 'Secretos en repos',
    desc: 'Busca API keys, tokens y contraseñas accidentalmente subidas a GitHub.',
  },
  {
    icon: Eye,
    title: 'Perspectiva del atacante',
    desc: 'Vemos tu empresa exactamente como la vería alguien intentando entrar.',
  },
]

function Features() {
  return (
    <section id="features" className="py-24 px-6 bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-black text-obsidian-900 mb-4">
            Todo lo que un atacante vería
          </h2>
          <p className="text-gray-500 text-lg max-w-xl mx-auto">
            Sajjad analiza 8 vectores de exposición en cada escaneo.
            Nada se queda sin revisar.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title}
              className="group bg-slate-50 hover:bg-obsidian-900 rounded-2xl p-6
                transition-all duration-300 cursor-default border border-transparent
                hover:border-obsidian-700">
              <div className="bg-obsidian-100 group-hover:bg-gold-500 w-10 h-10
                rounded-xl flex items-center justify-center mb-4 transition-colors">
                <Icon className="h-5 w-5 text-obsidian-700 group-hover:text-white
                  transition-colors" />
              </div>
              <h3 className="font-bold text-obsidian-900 group-hover:text-white mb-2
                transition-colors">
                {title}
              </h3>
              <p className="text-sm text-gray-500 group-hover:text-white/60
                leading-relaxed transition-colors">
                {desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const STEPS = [
  {
    n: '01',
    title: 'Agrega tu dominio',
    desc: 'Regístrate, ingresa el dominio de tu empresa y verifica que eres el dueño con un registro DNS TXT. Solo toma 2 minutos.',
    icon: Globe,
  },
  {
    n: '02',
    title: 'Sajjad escanea todo',
    desc: 'Nuestro pipeline de 9 etapas analiza subdominios, puertos, certificados, DNS, vulnerabilidades y fuentes OSINT automáticamente.',
    icon: Zap,
  },
  {
    n: '03',
    title: 'Recibe tu reporte',
    desc: 'En minutos tienes un Risk Score 0-100, todos los hallazgos clasificados por severidad y recomendaciones claras de qué corregir.',
    icon: FileText,
  },
]

function HowItWorks() {
  return (
    <section id="how" className="py-24 px-6 bg-slate-50">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-black text-obsidian-900 mb-4">
            Tan simple como tres pasos
          </h2>
          <p className="text-gray-500 text-lg">
            Sin agentes, sin instalaciones, sin configuración compleja.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {STEPS.map(({ n, title, desc, icon: Icon }, i) => (
            <div key={n} className="relative">
              {i < STEPS.length - 1 && (
                <div className="hidden md:block absolute top-10 left-full w-full
                  h-px bg-gradient-to-r from-obsidian-200 to-transparent z-0
                  -translate-x-4" />
              )}
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-4">
                  <div className="bg-obsidian-900 text-gold-400 font-black text-sm
                    w-8 h-8 rounded-full flex items-center justify-center shrink-0">
                    {n}
                  </div>
                  <div className="h-px flex-1 bg-obsidian-100" />
                </div>
                <div className="bg-white rounded-2xl border border-gray-100
                  shadow-sm p-6">
                  <Icon className="h-8 w-8 text-gold-500 mb-4" />
                  <h3 className="font-bold text-obsidian-900 text-lg mb-2">{title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: 30,
    desc: 'Para empresas pequeñas que quieren saber qué tienen expuesto.',
    domains: 1,
    interval: 'Escaneos semanales',
    features: [
      'Reporte PDF completo',
      'Risk Score 0-100',
      'Subdominios, puertos y TLS',
      'Análisis DNS y email',
      'Soporte por email',
    ],
    cta: 'Empezar con Starter',
    highlight: false,
  },
  {
    id: 'professional',
    name: 'Professional',
    price: 50,
    desc: 'Para empresas que necesitan monitoreo continuo y múltiples activos.',
    domains: 3,
    interval: 'Escaneos diarios',
    features: [
      'Todo lo del plan Starter',
      'Hasta 3 dominios',
      'Credenciales filtradas (HIBP)',
      'Secretos en GitHub',
      'Alertas por email en hallazgos críticos',
    ],
    cta: 'Empezar con Professional',
    highlight: true,
  },
  {
    id: 'agency',
    name: 'Agency',
    price: 120,
    desc: 'Para agencias de seguridad que monitorizan múltiples clientes.',
    domains: 10,
    interval: 'Escaneos diarios',
    features: [
      'Todo lo del plan Professional',
      'Hasta 10 dominios',
      'Reportes white-label',
      'API de acceso',
      'Soporte prioritario',
    ],
    cta: 'Hablar con ventas',
    highlight: false,
  },
]

function Pricing() {
  return (
    <section id="pricing" className="py-24 px-6 bg-white">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-black text-obsidian-900 mb-4">
            Precios claros, sin sorpresas
          </h2>
          <p className="text-gray-500 text-lg">
            Planes diseñados para empresas latinoamericanas.
            Cancela cuando quieras.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
          {PLANS.map(plan => (
            <div key={plan.id}
              className={`rounded-3xl p-8 border-2 relative ${
                plan.highlight
                  ? 'bg-obsidian-900 border-gold-500 scale-105 shadow-2xl'
                  : 'bg-white border-gray-100 shadow-sm'
              }`}>
              {plan.highlight && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2
                  bg-gold-500 text-white text-xs font-bold px-4 py-1
                  rounded-full uppercase tracking-widest">
                  Más popular
                </div>
              )}

              <h3 className={`font-black text-xl mb-1 ${
                plan.highlight ? 'text-white' : 'text-obsidian-900'
              }`}>
                {plan.name}
              </h3>
              <p className={`text-sm mb-6 ${
                plan.highlight ? 'text-white/50' : 'text-gray-400'
              }`}>
                {plan.desc}
              </p>

              <div className="mb-6">
                <span className={`text-5xl font-black ${
                  plan.highlight ? 'text-white' : 'text-obsidian-900'
                }`}>
                  ${plan.price}
                </span>
                <span className={`text-sm ml-1 ${
                  plan.highlight ? 'text-white/50' : 'text-gray-400'
                }`}>
                  USD/mes
                </span>
              </div>

              <div className={`text-xs font-bold uppercase tracking-widest mb-4 ${
                plan.highlight ? 'text-gold-400' : 'text-obsidian-700'
              }`}>
                {plan.domains} dominio{plan.domains > 1 ? 's' : ''} ·{' '}
                {plan.interval}
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map(f => (
                  <li key={f} className="flex items-start gap-2">
                    <Check className={`h-4 w-4 shrink-0 mt-0.5 ${
                      plan.highlight ? 'text-gold-400' : 'text-green-500'
                    }`} />
                    <span className={`text-sm ${
                      plan.highlight ? 'text-white/70' : 'text-gray-600'
                    }`}>
                      {f}
                    </span>
                  </li>
                ))}
              </ul>

              <Link to="/register"
                className={`block text-center font-bold py-3 px-6 rounded-xl
                  transition-all text-sm ${
                  plan.highlight
                    ? 'bg-gold-500 hover:bg-gold-400 text-obsidian-900'
                    : 'bg-obsidian-900 hover:bg-obsidian-800 text-white'
                }`}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function FinalCTA() {
  return (
    <section className="relative overflow-hidden py-24 px-6 bg-gradient-to-br
      from-obsidian-950 via-lapis-900 to-obsidian-900">
      <EyeOfHorus
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2
          w-[520px] text-gold-500/5 pointer-events-none"
        strokeWidth={2}
      />
      <div className="relative z-10 max-w-3xl mx-auto text-center">
        <div className="inline-flex items-center justify-center
          bg-gradient-to-br from-gold-400 to-gold-600 rounded-2xl p-4 mb-6
          shadow-gold">
          <EyeOfHorus className="h-10 w-14 text-obsidian-900" strokeWidth={5} />
        </div>
        <h2 className="text-4xl md:text-5xl font-black text-white mb-4">
          ¿Sabes qué tiene expuesto tu empresa ahora mismo?
        </h2>
        <p className="text-white/50 text-xl mb-10">
          En menos de 5 minutos tienes tu primer reporte.
          Sin tarjeta de crédito.
        </p>
        <Link to="/register"
          className="inline-flex items-center gap-2 bg-gold-500
            hover:bg-gold-400 text-obsidian-900 font-bold text-lg px-10 py-4
            rounded-xl transition-all hover:scale-105 shadow-gold">
          Empezar ahora — es gratis
          <ChevronRight className="h-5 w-5" />
        </Link>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="bg-slate-950 border-t border-white/5 px-6 py-10">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center
        justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 p-1 rounded-md bg-gradient-to-br
            from-gold-400 to-gold-600 flex items-center justify-center">
            <EyeOfHorus className="text-obsidian-900 w-full h-full" strokeWidth={6} />
          </div>
          <span className="text-white font-black">
            SAJJAD<span className="text-gold-500">.</span>
          </span>
          <span className="text-white/20 text-sm ml-2">
            Attack Surface Monitor
          </span>
        </div>
        <p className="text-white/20 text-sm">
          © {new Date().getFullYear()} Sajjad. Todos los derechos reservados.
        </p>
        <div className="flex items-center gap-6 text-white/30 text-sm">
          <a href="#features" className="hover:text-white/60 transition-colors">
            Características
          </a>
          <a href="#pricing" className="hover:text-white/60 transition-colors">
            Precios
          </a>
          <Link to="/login" className="hover:text-white/60 transition-colors">
            Login
          </Link>
        </div>
      </div>
    </footer>
  )
}

export function Landing() {
  return (
    <div className="font-sans">
      <Nav />
      <Hero />
      <Features />
      <HowItWorks />
      <Pricing />
      <FinalCTA />
      <Footer />
    </div>
  )
}
