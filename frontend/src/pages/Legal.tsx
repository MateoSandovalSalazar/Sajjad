/**
 * Páginas legales: Términos de Servicio y Política de Privacidad.
 *
 * IMPORTANTE: son borradores de trabajo, redactados para cubrir lo
 * que el producto hace de verdad. Antes de vender a clientes de pago
 * deben pasar por un abogado — sobre todo las secciones de
 * responsabilidad y jurisdicción, que dependen de dónde quede
 * constituida la empresa.
 */
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { EyeOfHorus } from '../components/ui/EyeOfHorus'

const CONTACT_EMAIL = 'legal@sajjad.app'
const LAST_UPDATED = '5 de agosto de 2026'

function LegalShell({ title, children }: {
  title: string
  children: React.ReactNode
}) {
  useDocumentTitle(title)

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-100 px-6 py-5">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <EyeOfHorus className="h-6 w-9 text-obsidian-900" strokeWidth={5} />
            <span className="font-black text-obsidian-900">SAJJAD</span>
          </Link>
          <Link to="/"
            className="text-sm text-gray-500 hover:text-obsidian-900
              inline-flex items-center gap-1.5 transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl md:text-4xl font-black text-obsidian-900 mb-2">
          {title}
        </h1>
        <p className="text-sm text-gray-400 mb-10">
          Última actualización: {LAST_UPDATED}
        </p>
        <div className="legal-prose space-y-8">{children}</div>
      </main>

      <footer className="border-t border-gray-100 px-6 py-8 mt-12">
        <div className="max-w-3xl mx-auto flex flex-wrap gap-x-6 gap-y-2
          text-sm text-gray-400">
          <Link to="/legal/terminos" className="hover:text-obsidian-900">
            Términos de Servicio
          </Link>
          <Link to="/legal/privacidad" className="hover:text-obsidian-900">
            Política de Privacidad
          </Link>
          <a href={`mailto:${CONTACT_EMAIL}`}
            className="hover:text-obsidian-900">
            {CONTACT_EMAIL}
          </a>
        </div>
      </footer>
    </div>
  )
}

function Section({ n, title, children }: {
  n: string
  title: string
  children: React.ReactNode
}) {
  return (
    <section>
      <h2 className="text-lg font-bold text-obsidian-900 mb-3">
        {n}. {title}
      </h2>
      <div className="space-y-3 text-gray-600 leading-relaxed text-[15px]">
        {children}
      </div>
    </section>
  )
}

export function Terms() {
  return (
    <LegalShell title="Términos de Servicio">
      <div className="rounded-xl border-2 border-gold-500/40 bg-gold-50/50
        px-5 py-4">
        <p className="text-sm text-obsidian-900 font-semibold mb-1">
          Lo esencial, en una frase
        </p>
        <p className="text-sm text-gray-700">
          Sajjad analiza únicamente dominios que tú posees y has
          verificado. Usarlo contra infraestructura ajena sin
          autorización es una violación de estos términos y,
          probablemente, de la ley de tu país.
        </p>
      </div>

      <Section n="1" title="Qué es Sajjad">
        <p>
          Sajjad es un servicio de monitoreo de superficie de ataque
          externa (EASM). Analiza la infraestructura que tu
          organización expone públicamente a internet —subdominios,
          puertos, certificados TLS, configuración DNS de correo,
          vulnerabilidades conocidas— y emite un informe con un Risk
          Score y recomendaciones de remediación.
        </p>
        <p>
          Sajjad realiza <strong>detección, no explotación</strong>. No
          intenta vulnerar sistemas, no extrae datos, no realiza
          ataques de denegación de servicio ni pruebas intrusivas.
        </p>
      </Section>

      <Section n="2" title="Autorización de escaneo (cláusula esencial)">
        <p>
          Al registrar un dominio declaras, bajo tu responsabilidad,
          que <strong>eres el propietario de ese dominio o cuentas con
          autorización expresa y por escrito de su propietario</strong>
          para que sea analizado.
        </p>
        <p>
          Esta declaración queda registrada con fecha, hora y dirección
          IP. Además, antes de habilitar cualquier escaneo, exigimos
          que demuestres control técnico del dominio publicando un
          registro DNS TXT único que nosotros generamos. Ambos
          requisitos son obligatorios y no se pueden omitir.
        </p>
        <p>
          <strong>Asumes toda la responsabilidad legal</strong> derivada
          de analizar un dominio sobre el que no tenías autorización.
          Si detectamos o sospechamos un uso de este tipo, podemos
          suspender la cuenta de inmediato y sin reembolso, y colaborar
          con las autoridades competentes si nos lo requieren.
        </p>
      </Section>

      <Section n="3" title="Tu cuenta">
        <p>
          Eres responsable de mantener la confidencialidad de tus
          credenciales y de toda la actividad que ocurra bajo tu
          cuenta. Avísanos de inmediato a {CONTACT_EMAIL} si detectas
          un acceso no autorizado.
        </p>
        <p>
          Debes proporcionar información veraz al registrarte y ser
          mayor de edad en tu jurisdicción, o actuar en nombre de una
          entidad con capacidad legal para aceptar estos términos.
        </p>
      </Section>

      <Section n="4" title="Planes, prueba gratuita y pagos">
        <p>
          Ofrecemos una prueba gratuita por tiempo limitado que se
          activa al verificar tu correo electrónico. Al terminar, la
          cuenta pasa automáticamente al plan gratuito.{' '}
          <strong>No se realiza ningún cargo automático</strong> ni se
          solicitan datos de tarjeta para la prueba.
        </p>
        <p>
          Los planes de pago se facturan por adelantado y de forma
          recurrente. Puedes cancelar en cualquier momento; la
          cancelación surte efecto al final del periodo ya pagado y no
          genera reembolsos por el tiempo no utilizado, salvo que la
          ley aplicable disponga otra cosa.
        </p>
        <p>
          Los precios están expresados en dólares estadounidenses (USD)
          y no incluyen los impuestos que pudieran corresponder según
          tu país.
        </p>
      </Section>

      <Section n="5" title="Uso aceptable">
        <p>Te comprometes a no utilizar Sajjad para:</p>
        <ul className="list-disc pl-5 space-y-1.5">
          <li>
            Analizar infraestructura sobre la que no tienes propiedad
            ni autorización escrita.
          </li>
          <li>
            Intentar eludir la verificación de propiedad de dominios
            por cualquier medio.
          </li>
          <li>
            Sobrecargar, interferir o intentar acceder sin autorización
            a los sistemas de Sajjad.
          </li>
          <li>
            Revender, sublicenciar o redistribuir el servicio, salvo lo
            expresamente permitido en el plan Agency.
          </li>
          <li>
            Cualquier finalidad ilícita o contraria a la normativa
            aplicable en tu jurisdicción.
          </li>
        </ul>
      </Section>

      <Section n="6" title="Limitaciones del servicio">
        <p>
          Sajjad es una herramienta de apoyo, no un sustituto de una
          auditoría de seguridad profesional ni de un programa de
          gestión de vulnerabilidades.{' '}
          <strong>
            Un informe sin hallazgos no significa que tu
            infraestructura sea segura
          </strong>
          : significa que nuestras comprobaciones automatizadas no
          detectaron nada en ese momento.
        </p>
        <p>
          El servicio se presta &laquo;tal cual&raquo;. No garantizamos
          detección exhaustiva, ausencia de falsos positivos ni
          disponibilidad ininterrumpida.
        </p>
      </Section>

      <Section n="7" title="Limitación de responsabilidad">
        <p>
          En la máxima medida permitida por la ley, no seremos
          responsables por daños indirectos, incidentales, especiales
          o consecuentes, ni por lucro cesante o pérdida de datos,
          derivados del uso o de la imposibilidad de uso del servicio.
        </p>
        <p>
          Nuestra responsabilidad total y acumulada no excederá el
          importe que hayas pagado por el servicio durante los doce
          (12) meses anteriores al hecho que origine la reclamación.
        </p>
      </Section>

      <Section n="8" title="Suspensión y terminación">
        <p>
          Puedes cerrar tu cuenta cuando quieras desde la sección Mi
          cuenta. Podemos suspender o cerrar cuentas que incumplan
          estos términos, con aviso previo salvo en casos de uso
          indebido manifiesto o riesgo para terceros, donde la
          suspensión puede ser inmediata.
        </p>
      </Section>

      <Section n="9" title="Cambios en los términos">
        <p>
          Podemos actualizar estos términos. Si el cambio es
          sustancial, te avisaremos por correo electrónico con al menos
          30 días de antelación. Seguir usando el servicio tras la
          entrada en vigor implica aceptación.
        </p>
      </Section>

      <Section n="10" title="Contacto">
        <p>
          Para cualquier duda sobre estos términos, escríbenos a{' '}
          <a href={`mailto:${CONTACT_EMAIL}`}
            className="text-obsidian-900 underline">
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </Section>
    </LegalShell>
  )
}

export function Privacy() {
  return (
    <LegalShell title="Política de Privacidad">
      <div className="rounded-xl border-2 border-gold-500/40 bg-gold-50/50
        px-5 py-4">
        <p className="text-sm text-obsidian-900 font-semibold mb-1">
          Lo esencial, en una frase
        </p>
        <p className="text-sm text-gray-700">
          Guardamos lo mínimo para prestarte el servicio, no vendemos
          tus datos a nadie, y los resultados de tus escaneos son
          tuyos.
        </p>
      </div>

      <Section n="1" title="Qué datos recogemos">
        <p><strong>Datos de cuenta.</strong> Correo electrónico, nombre
        y, si lo indicas, empresa. Tu contraseña se almacena únicamente
        como hash bcrypt: no la conocemos ni podemos recuperarla.</p>

        <p><strong>Datos de tus dominios.</strong> Los dominios que
        registras y los resultados de sus escaneos: subdominios,
        direcciones IP, puertos abiertos, certificados, cabeceras HTTP
        y hallazgos de seguridad. Toda esta información es pública por
        definición —es lo que cualquiera puede ver desde internet—,
        pero la tratamos como confidencial porque su agregación sí
        resulta sensible.</p>

        <p><strong>Registro de autorización.</strong> Al declarar la
        propiedad de un dominio guardamos la fecha, la dirección IP y
        el navegador desde el que hiciste la declaración. Es una
        obligación de diligencia por nuestra parte y tu respaldo
        documental.</p>

        <p><strong>Datos técnicos.</strong> Registros de acceso a la
        API con dirección IP y marca de tiempo, para seguridad
        operativa y detección de abuso.</p>
      </Section>

      <Section n="2" title="Para qué los usamos">
        <ul className="list-disc pl-5 space-y-1.5">
          <li>Prestar el servicio de monitoreo y generar tus informes.</li>
          <li>
            Enviarte avisos operativos: verificación de correo,
            restablecimiento de contraseña, alertas de hallazgos
            críticos y estado de tu plan.
          </li>
          <li>Prevenir abuso, fraude y accesos no autorizados.</li>
          <li>Cumplir obligaciones legales cuando corresponda.</li>
        </ul>
        <p>
          <strong>No usamos tus datos para publicidad</strong> ni los
          cedemos a terceros con fines comerciales.
        </p>
      </Section>

      <Section n="3" title="Con quién los compartimos">
        <p>
          Sólo con los proveedores estrictamente necesarios para operar,
          y únicamente en la medida en que lo necesitan:
        </p>
        <ul className="list-disc pl-5 space-y-1.5">
          <li>Proveedor de infraestructura (alojamiento del servicio).</li>
          <li>Proveedor de correo transaccional (envío de avisos).</li>
          <li>
            Pasarela de pagos, cuando contrates un plan de pago. Los
            datos de tu tarjeta se procesan directamente en la
            pasarela: <strong>nunca pasan por nuestros servidores ni
            los almacenamos</strong>.
          </li>
        </ul>
        <p>
          También podemos divulgar información si una autoridad
          competente nos lo requiere legalmente.
        </p>
      </Section>

      <Section n="4" title="Durante cuánto tiempo">
        <p>
          Conservamos los datos de tu cuenta y los resultados de tus
          escaneos mientras la cuenta esté activa. Si la cierras, los
          eliminamos en un plazo máximo de 30 días, salvo aquello que
          debamos conservar por obligación legal (por ejemplo, registros
          de facturación).
        </p>
      </Section>

      <Section n="5" title="Tus derechos">
        <p>
          Puedes acceder a tus datos, rectificarlos, exportarlos o
          solicitar su supresión. Desde la sección Mi cuenta puedes
          editar tu perfil y eliminar la cuenta. Para cualquier otra
          solicitud escríbenos a{' '}
          <a href={`mailto:${CONTACT_EMAIL}`}
            className="text-obsidian-900 underline">
            {CONTACT_EMAIL}
          </a>
          {' '}y responderemos en un plazo máximo de 30 días.
        </p>
      </Section>

      <Section n="6" title="Seguridad">
        <p>
          Somos una empresa de seguridad y nos aplicamos nuestras
          propias reglas: cifrado TLS en todo el tráfico, contraseñas
          con hash bcrypt, tokens de sesión de corta duración que se
          invalidan al cambiar la contraseña, límites de peticiones
          contra fuerza bruta y copias de seguridad cifradas.
        </p>
        <p>
          Ningún sistema es infalible. Si detectamos una brecha que
          afecte a tus datos, te lo comunicaremos sin demora indebida.
        </p>
      </Section>

      <Section n="7" title="Reportar una vulnerabilidad">
        <p>
          Si encuentras un fallo de seguridad en Sajjad, escríbenos a{' '}
          <a href={`mailto:${CONTACT_EMAIL}`}
            className="text-obsidian-900 underline">
            {CONTACT_EMAIL}
          </a>
          . Agradecemos la divulgación responsable y no emprenderemos
          acciones legales contra quien investigue de buena fe, sin
          acceder a datos de terceros ni degradar el servicio.
        </p>
      </Section>

      <Section n="8" title="Cambios">
        <p>
          Si modificamos esta política de forma sustancial te
          avisaremos por correo electrónico antes de que entre en
          vigor.
        </p>
      </Section>
    </LegalShell>
  )
}
