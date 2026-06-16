# SAJJAD — Attack Surface Monitor
# Contexto completo del proyecto para Claude Code

---

## QUÉ ES SAJJAD

Sajjad es un SaaS de monitoreo continuo de superficie de
ataque externa (External Attack Surface Management / EASM)
dirigido a PYMEs latinoamericanas.

El nombre viene de Al-Sajjad — "el que se postra en
vigilancia constante".

El producto monitorea lo que un atacante vería desde afuera
de la organización del cliente: subdominios expuestos,
puertos abiertos, servicios mal configurados, certificados
vencidos, credenciales filtradas, secretos en repositorios
públicos. Todo de forma automática y continua.

### El problema que resuelve
Las empresas no saben qué tienen expuesto. Plataformas
profesionales como Censys o SecurityScorecard cuestan miles
de dólares al mes — inaccesibles para PYMEs. No existe
una alternativa seria, accesible y en español para el
mercado latinoamericano.

### Modelo de negocio
- Plan Starter: $30 USD/mes — 1 dominio, scans semanales
- Plan Professional: $50 USD/mes — 3 dominios, scans diarios
- Plan Agency: $120 USD/mes — 10 dominios, white-label

### Desarrollador
Solo yo. Proyecto unipersonal. Sin cofundador, sin equipo.

---

## REGLA CRÍTICA — AUTORIZACIÓN Y ALCANCE

Sajjad SOLO escanea dominios que el cliente posee y ha
verificado como suyos mediante un token DNS TXT único.
Esta regla nunca se rompe ni se negocia.

Verificación de propiedad:
1. Cliente registra su dominio
2. Sajjad genera token único (sajjad-verify-XXXXXXXX)
3. Cliente crea registro DNS TXT con ese token
4. Sajjad verifica el token antes de habilitar escaneos

Safeguards adicionales:
- Rate limiting en todos los escaneos
- Scope estricto — nunca fuera de activos verificados
- nuclei solo en modo detección segura, no explotación

---

## ARQUITECTURA DEL SISTEMA

### Filosofía de diseño
Sajjad es un ORQUESTADOR en Python. No reinventa
herramientas — encadena las mejores herramientas
existentes (ProjectDiscovery suite + nmap) y agrega
el valor en la lógica de correlación, scoring y reporte.

### Stack tecnológico completo

Backend:
- Python 3.12
- uv (gestión de dependencias y entornos virtuales)
- FastAPI (API REST) — Fase 1+
- Celery + Redis (tareas asíncronas) — Fase 1+
- PostgreSQL 16 (base de datos) — Fase 1+
- WeasyPrint o ReportLab (generación de PDFs)

Frontend (Fase 2+):
- React 18 + TypeScript
- Tailwind CSS

Infraestructura:
- Docker + Docker Compose
- GitHub (control de versiones)

Herramientas de escaneo (todas instaladas en el sistema):
- subfinder (descubrimiento de subdominios)
- dnsx (resolución DNS)
- httpx (probing HTTP/HTTPS)
- naabu (escaneo de puertos — rápido)
- nmap (detección de servicios — profundo)
- tlsx (análisis de certificados TLS)
- nuclei (detección de vulnerabilidades con templates)
- amass (enumeración adicional cuando se necesita)

APIs externas:
- Have I Been Pwned (credenciales filtradas)
- GitHub API (secretos en repos públicos)
- Shodan API (perspectiva externa pasiva)
- crt.sh (Certificate Transparency logs)

---

## EL PIPELINE DE ESCANEO

El corazón de Sajjad. Cada etapa toma la salida de la
anterior como entrada. Filosofía Unix aplicada a ASM.

```
ENTRADA: dominio del cliente (ej: empresa.com)

ETAPA 1 — DESCUBRIMIENTO
subfinder + crt.sh + amass
→ lista de subdominios candidatos

ETAPA 2 — RESOLUCIÓN DNS
dnsx
→ subdominios vivos con sus IPs
→ detección de dangling records (subdomain takeover risk)

ETAPA 3 — PROBING HTTP
httpx
→ URLs activas
→ status codes, títulos, tecnologías
→ headers de seguridad (presentes/faltantes)
→ info TLS básica

ETAPA 4 — ESCANEO DE PUERTOS
naabu (SYN scan rápido) → lista de puertos abiertos
nmap (service detection profundo) → servicios + versiones

ETAPA 5 — ANÁLISIS TLS
tlsx
→ fechas de expiración de certificados
→ cipher suites débiles
→ cadena de confianza
→ SANs (revela subdominios adicionales)

ETAPA 6 — ANÁLISIS DNS DE CORREO
consultas DNS directas
→ registros SPF (presencia y configuración)
→ registros DKIM
→ registros DMARC
→ riesgo de email spoofing

ETAPA 7 — DETECCIÓN DE VULNERABILIDADES
nuclei (templates comunitarios)
→ paneles de admin expuestos
→ tecnologías vulnerables
→ configuraciones por defecto
→ archivos sensibles accesibles
→ CVEs conocidos

ETAPA 8 — ENRIQUECIMIENTO EXTERNO
HIBP API → credenciales filtradas (emails corporativos)
GitHub API → secretos en repos públicos (dorking)
Shodan API → perspectiva externa pasiva

ETAPA 9 — CONSOLIDACIÓN Y SCORING
→ todos los findings normalizados
→ clasificación por severidad (critical/high/medium/low/info)
→ cálculo de Risk Score 0-100
→ deduplicación

SALIDA: findings + risk score → PDF o base de datos
```

---

## CÓMO EJECUTAR CADA HERRAMIENTA

Todos los binarios de ProjectDiscovery están en ~/go/bin.
Todos soportan output JSON con el flag -json.

### subfinder
```
subfinder -d empresa.com -silent -json
```
Output JSON por línea, campo relevante: "host"
Fuentes: SecurityTrails, Censys, VirusTotal, HackerTarget,
y ~40 fuentes más configuradas en ~/.config/subfinder/

### dnsx
```
dnsx -l subdominios.txt -json -silent
```
Recibe lista de subdominios, resuelve cuáles viven.
Output JSON por línea: host, resolver, a (IPs)

### httpx
```
httpx -l hosts_vivos.txt -json -silent \
  -title -tech-detect -status-code \
  -web-server -content-type -no-color
```
Output JSON por línea con toda la metadata web.

### naabu
```
naabu -host empresa.com -json -silent \
  -top-ports 1000
```
Puertos más comunes primero. Output JSON: ip, port.

### nmap (después de naabu)
```
nmap -sV -sC -p PUERTOS_ABIERTOS \
  --open -oJ - TARGET_IP
```
-sV detecta versiones. -sC scripts básicos.
-oJ - output JSON a stdout.

### tlsx
```
tlsx -u empresa.com -json -silent \
  -expired -self-signed -mismatched
```
Flags de checks específicos de seguridad TLS.

### nuclei
```
nuclei -u https://empresa.com \
  -severity critical,high,medium \
  -json -silent \
  -exclude-tags dos,fuzz,intrusive
```
CRÍTICO: siempre excluir tags dos, fuzz, intrusive.
Solo detección segura, nunca explotación.

---

## ESTRUCTURA DEL PROYECTO

```
sajjad/
├── CLAUDE.md                  ← este archivo
├── sajjad.py                  ← CLI principal (MVP Fase 0)
├── sajjad/                    ← paquete principal
│   ├── __init__.py
│   ├── orchestrator.py        ← orquestador del pipeline
│   ├── scanners/              ← conectores de herramientas
│   │   ├── __init__.py
│   │   ├── subdomain.py       ← subfinder + crt.sh
│   │   ├── dns.py             ← dnsx
│   │   ├── http.py            ← httpx
│   │   ├── ports.py           ← naabu + nmap
│   │   ├── tls.py             ← tlsx
│   │   ├── vulns.py           ← nuclei
│   │   └── osint.py           ← HIBP, GitHub, Shodan
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── normalizer.py      ← normaliza outputs a formato común
│   │   ├── scorer.py          ← cálculo del Risk Score
│   │   └── deduplicator.py    ← elimina findings duplicados
│   ├── reporting/
│   │   ├── __init__.py
│   │   └── pdf_generator.py   ← genera el PDF del reporte
│   └── models/                ← dataclasses/Pydantic models
│       ├── __init__.py
│       ├── finding.py         ← modelo de un finding
│       ├── scan_result.py     ← resultado completo de scan
│       └── report.py          ← estructura del reporte
├── tests/
│   └── __init__.py
├── pyproject.toml
└── .env                       ← API keys (nunca a Git)
```

---

## MODELOS DE DATOS CLAVE

### Finding (un hallazgo individual)
```python
@dataclass
class Finding:
    id: str                   # UUID
    category: str             # subdomain|port|cert|cred|
                              # dns|vuln|cloud|osint
    severity: str             # critical|high|medium|low|info
    title: str                # título corto
    description: str          # descripción técnica
    evidence: dict            # datos crudos de la herramienta
    recommendation: str       # qué hacer para remediarlo
    cvss_score: float | None  # si aplica
    cve: str | None           # si aplica
    source_tool: str          # qué herramienta lo encontró
    host: str                 # subdominio o IP afectada
    port: int | None          # puerto si aplica
    discovered_at: datetime
```

### ScanResult (resultado completo de un escaneo)
```python
@dataclass
class ScanResult:
    domain: str
    scan_id: str
    started_at: datetime
    completed_at: datetime
    subdomains: list[str]
    live_hosts: list[str]
    open_ports: dict          # host -> [puertos]
    findings: list[Finding]
    risk_score: int           # 0-100
    risk_level: str           # critical|high|medium|low
    summary: dict             # conteos por severidad
```

---

## SISTEMA DE RISK SCORING

El Risk Score (0-100) se calcula así:

Base por severidad de findings:
- Critical finding: +25 puntos (cap: 100)
- High finding: +10 puntos
- Medium finding: +3 puntos
- Low finding: +1 punto
- Info finding: +0 puntos

Multiplicadores:
- Credencial filtrada activa: ×1.5
- Certificado vencido: +15 fijo
- Puerto de base de datos expuesto directamente: +20 fijo
- Más de 10 subdominios expuestos: +5
- Sin registros SPF/DMARC: +8

Niveles resultantes:
- 0-25: Low
- 26-50: Medium
- 51-75: High
- 76-100: Critical

La lógica de scoring vive en sajjad/analysis/scorer.py.

---

## CLASIFICACIÓN DE SEVERIDADES

### Critical
- RCE (remote code execution) detectado
- Credenciales válidas expuestas
- Panel de admin con acceso sin autenticación
- Base de datos expuesta directamente a internet

### High
- Certificado SSL vencido
- Subdomain takeover posible (dangling DNS)
- Versión de servicio con CVE activo
- Sin DMARC (riesgo de email spoofing total)
- Archivos de configuración accesibles

### Medium
- Certificado SSL por vencer (<30 días)
- Puerto inusual abierto (RDP, VNC expuestos)
- Headers de seguridad HTTP faltantes
- SPF mal configurado
- Tecnología desactualizada sin CVE conocido

### Low
- Subdominios olvidados que responden
- Información de versión expuesta en headers
- Redirecciones inseguras

### Info
- Subdominios descubiertos (inventario)
- Puertos abiertos esperados (80, 443)
- Tecnologías detectadas (sin vulnerabilidad)

---

## CONVENCIONES DE CÓDIGO

### Estilo general
- Python 3.12 con type hints en todo
- Dataclasses o Pydantic para modelos de datos
- Funciones pequeñas con una sola responsabilidad
- Nombres descriptivos en inglés para código,
  comentarios en español si es necesario
- Máximo 80 caracteres por línea
- Formateo con black, linting con ruff

### Manejo de subprocesos
Siempre usar subprocess.run con timeout y manejo de errores:

```python
import subprocess
import json

def run_tool(cmd: list[str], timeout: int = 300) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise ScanTimeoutError(f"Timeout: {' '.join(cmd)}")
    except FileNotFoundError:
        raise ToolNotFoundError(f"Herramienta no encontrada: {cmd[0]}")
```

### Parsing de JSON line-by-line
La mayoría de herramientas de PD emiten un JSON por línea
(JSONL), no un array. Parsear así:

```python
def parse_jsonl(output: str) -> list[dict]:
    results = []
    for line in output.strip().splitlines():
        if line.strip():
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return results
```

### Logs
Usar el módulo logging estándar, no print():

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Iniciando subfinder para %s", domain)
```

---

## VARIABLES DE ENTORNO REQUERIDAS

Definidas en .env (nunca en Git):

```
# APIs externas
HIBP_API_KEY=tu_clave_hibp
GITHUB_TOKEN=tu_personal_access_token
SHODAN_API_KEY=tu_clave_shodan

# Configuración de escaneo
SCAN_TIMEOUT=300
MAX_CONCURRENT_SCANS=3
NUCLEI_RATE_LIMIT=150

# PostgreSQL (Fase 1+)
DATABASE_URL=postgresql://sajjad:password@localhost:5432/sajjad_db

# Redis (Fase 1+)
REDIS_URL=redis://localhost:6379/0
```

---

## ESTADO ACTUAL DEL PROYECTO Y FASES

### Fase 0 — MVP CLI (ACTUAL)
Un script que toma un dominio y genera un PDF.
Sin base de datos, sin web, solo el motor.

Uso objetivo:
```
python sajjad.py --domain empresa.com --output reporte.pdf
```

Entregable: reporte PDF profesional con:
- Subdominios descubiertos
- Puertos y servicios abiertos
- Estado de certificados TLS
- Análisis DNS (SPF/DKIM/DMARC)
- Headers de seguridad faltantes
- Vulnerabilidades detectadas por nuclei
- Credenciales filtradas (HIBP)
- Risk Score global (0-100)
- Recomendaciones de remediación

### Fase 1 — Backend API (siguiente)
- FastAPI + PostgreSQL + Celery
- Verificación de propiedad de dominios (DNS TXT)
- Scans programados automáticos
- Almacenamiento de histórico
- Alertas por email en nuevos findings críticos

### Fase 2 — Frontend Dashboard
- React + TypeScript
- Dashboard con Risk Score y tendencias
- Vista detallada de findings
- Generación de reportes PDF desde UI

### Fase 3 — Producto comercial
- Landing page
- Billing (MercadoPago / Stripe)
- Onboarding de nuevos clientes
- Primeros clientes de pago

### Fase 4 — Módulos avanzados
- Cloud exposure (S3, Azure, GCP)
- Comparación con benchmarks del sector
- Webhook integrations (Slack, Teams)
- API pública

---

## HERRAMIENTAS VERIFICAR ANTES DE USAR

Antes de ejecutar cualquier scanner, verificar que la
herramienta esté disponible en el sistema:

```python
import shutil

REQUIRED_TOOLS = [
    "subfinder", "dnsx", "httpx",
    "naabu", "nmap", "tlsx", "nuclei",
]

def verify_tools():
    missing = [t for t in REQUIRED_TOOLS if not shutil.which(t)]
    if missing:
        raise EnvironmentError(
            f"Herramientas faltantes: {', '.join(missing)}"
        )
```

Instalación en Arch Linux:
- ProjectDiscovery tools: go install ...@latest
  Binarios en ~/go/bin (debe estar en PATH)
- nmap: sudo pacman -S nmap
- amass: yay -S amass
- nuclei templates: nuclei -update-templates

---

## INSTRUCCIONES PARA CLAUDE CODE

- Siempre explicar el POR QUÉ de cada decisión técnica,
  no solo el cómo
- Mantener líneas de código bajo 80 caracteres
- Cuando escribas subprocesos, siempre incluir timeout
  y manejo de errores
- Los scanners van en sajjad/scanners/
- La lógica de negocio (scoring, normalización) va en
  sajjad/analysis/
- El PDF va en sajjad/reporting/
- Los modelos de datos van en sajjad/models/
- Nunca hardcodear API keys — siempre desde .env
- Ante cualquier duda sobre alcance ético de un escaneo,
  la respuesta es NO escanearlo
- El proyecto es solo mío — sin cofundadores ni equipo
- Priorizar código funcional y claro sobre código perfecto
- Añadir type hints en todas las funciones
