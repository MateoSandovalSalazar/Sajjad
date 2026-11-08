# Sajjad — Attack Surface Monitor

Monitoreo continuo de superficie de ataque externa (EASM) para PYMEs
latinoamericanas. Sajjad escanea lo que un atacante vería desde fuera
de tu organización —subdominios expuestos, puertos abiertos,
certificados vencidos, DNS de correo mal configurado, vulnerabilidades
conocidas, credenciales filtradas— y lo entrega como un Risk Score de
0 a 100 con recomendaciones concretas de remediación.

El nombre viene de Al-Sajjad, *"el que se postra en vigilancia
constante"*.

---

## Regla de alcance — no negociable

**Sajjad sólo escanea dominios que el cliente posee y ha verificado
como suyos** mediante un registro DNS TXT único.

1. El cliente registra su dominio.
2. Sajjad genera un token (`sajjad-verify-XXXXXXXX`).
3. El cliente crea un registro TXT **en la raíz del dominio** con ese
   token.
4. Sajjad verifica el token antes de habilitar ningún escaneo.

Además: rate limiting en todos los escaneos, alcance estricto a
activos verificados, y `nuclei` siempre en modo detección segura
(`-exclude-tags dos,fuzz,intrusive`) — nunca explotación.

Esta regla está protegida por CI: el workflow falla si aparece
cualquier endpoint de escaneo sin autenticar.

---

## Arquitectura

Sajjad es un **orquestador**. No reinventa herramientas: encadena la
suite de ProjectDiscovery y nmap, y aporta el valor en la correlación,
el scoring y el reporte.

```
                    ┌─────────────┐
   Navegador ──────▶│    Caddy    │ TLS, SPA estática, cabeceras
                    └──────┬──────┘
                           │ /api/*
                    ┌──────▼──────┐      ┌──────────────┐
                    │  FastAPI    │─────▶│  PostgreSQL  │
                    │  (API REST) │      └──────────────┘
                    └──────┬──────┘
                           │ encola             ┌────────────┐
                    ┌──────▼──────┐             │   Redis    │
                    │   Celery    │◀────────────┤  (broker)  │
                    │   worker    │             └─────▲──────┘
                    └──────┬──────┘                   │
                           │                    ┌─────┴──────┐
                           │                    │ Celery     │
                           │                    │ beat       │
                    ┌──────▼───────────────┐    └────────────┘
                    │ Pipeline de escaneo  │
                    │ (paquete `sajjad/`)  │
                    │ subfinder → dnsx →   │
                    │ httpx → naabu/nmap → │
                    │ tlsx → DNS correo →  │
                    │ nuclei → OSINT →     │
                    │ scoring → PDF        │
                    └──────────────────────┘
```

### Stack

| Capa | Tecnología |
|---|---|
| Motor de escaneo | Python 3.12, subprocess sobre ProjectDiscovery + nmap |
| API | FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2 |
| Tareas | Celery + Redis (worker y beat) |
| Base de datos | PostgreSQL 16 |
| Frontend | React 19 + TypeScript + Tailwind + Vite |
| Infra | Docker Compose, Caddy (TLS automático) |
| Gestión Python | uv |

### Estructura del repositorio

```
sajjad/
├── sajjad/               # Motor de escaneo (paquete importable)
│   ├── scanners/         # Un conector por herramienta
│   ├── analysis/         # Normalización, scoring, deduplicación
│   ├── reporting/        # Generación de PDF
│   └── models/           # Finding, ScanResult, Report
├── backend/              # API + worker
│   ├── app/
│   │   ├── core/         # limits.py (planes), security.py, exceptions
│   │   ├── models/       # SQLAlchemy
│   │   ├── routers/      # auth, users, domains, scans, billing
│   │   ├── services/     # auth, email, verificación DNS, MercadoPago
│   │   └── workers/      # Tareas Celery
│   ├── alembic/          # Migraciones
│   └── tests/            # 85 tests
├── frontend/             # Dashboard React
└── .github/workflows/    # CI
```

---

## Puesta en marcha (desarrollo)

Requisitos: Docker, Node 22, uv, y las herramientas de
ProjectDiscovery en `~/go/bin` (`subfinder`, `dnsx`, `httpx`, `naabu`,
`tlsx`, `nuclei`) más `nmap`.

```bash
# 1. Configuración
cp backend/.env.example backend/.env
# Edita backend/.env: SMTP (Mailtrap sirve) y API_SECRET_KEY

# 2. Levantar el stack
make up          # postgres, redis, api, worker, beat + migraciones

# 3. Frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```

La API queda en http://localhost:8000 y la documentación interactiva
en http://localhost:8000/docs.

### Comandos frecuentes

```bash
make up          # Levanta el stack de desarrollo
make down        # Lo detiene
make logs        # Sigue los logs de la API
make test        # Tests de backend + motor
make lint        # ruff + eslint + tsc
make migrate     # Aplica migraciones
make shell       # psql dentro del contenedor
```

### CLI del motor (sin API ni base de datos)

```bash
uv run python sajjad.py --domain tudominio.com --output reporte.pdf
```

---

## Planes y facturación

Los límites de cada plan viven en un único sitio,
`backend/app/core/limits.py`. La API los expone en
`GET /billing/subscription` y el frontend los consume desde ahí — no
hay una segunda copia que pueda desincronizarse.

| Plan | Precio | Dominios | Escaneos/mes | Intervalo | Hallazgos | PDF |
|---|---|---|---|---|---|---|
| Free | $0 | 1 | 1 | manual | ✗ | ✗ |
| **Prueba** | $0 · 14 días | 3 | 10 | diario | ✓ | ✓ |
| Starter | $30 | 1 | 4 | semanal | ✓ | ✓ |
| Professional | $50 | 3 | 30 | diario | ✓ | ✓ |
| Agency | $120 | 10 | 300 | diario | ✓ | ✓ + white-label |

La **prueba gratuita** se otorga al verificar el email (no al
registrarse: exigir un email verificado evita cadenas de cuentas
desechables). Expira sola por un beat diario, y además se degrada de
forma perezosa en cada request para que no queden hasta 24 h de
capacidades de pago regaladas entre ejecuciones del beat.

### Activar los pagos

Los pagos están **desactivados a propósito** por ahora. Con
`BILLING_ENABLED=false`:

- `POST /billing/checkout` → `503 BillingDisabled`
- `POST /billing/cancel` → `503 BillingDisabled`
- `POST /billing/webhook` → `404` (la ruta no existe para el mundo)
- La UI ofrece "Contactar para contratar" en lugar del botón de pago

Todo el resto del producto funciona: registro, prueba, escaneos,
hallazgos y PDF.

**Para activarlos, cuando llegue el momento:**

```bash
# En backend/.env
MP_ACCESS_TOKEN=APP_USR-...      # Panel de MercadoPago
MP_WEBHOOK_SECRET=...            # Panel → Webhooks → clave secreta
BILLING_ENABLED=true
```

Reinicia la API. **No hay que tocar código.** El flujo de
checkout/webhook/cancelación está implementado y cubierto por tests
en ambos modos.

En producción, `BILLING_ENABLED=true` sin esas dos credenciales hace
que la API se niegue a arrancar — un fallo ruidoso al desplegar es
preferible a uno silencioso en caliente.

---

## Despliegue

Ver [`docs/DEPLOY.md`](docs/DEPLOY.md) para la guía completa de
despliegue en VPS con Docker Compose y Caddy.

---

## Tests

```bash
make test
```

85 tests en el backend (auth, dominios, escaneos, límites de plan,
prueba gratuita, worker Celery, firma HMAC de webhooks, restablecer
contraseña) más los del motor de scoring y deduplicación.

El CI ejecuta en cada push: ruff, pytest (backend y motor), tsc,
eslint, build del frontend y los guardarraíles de alcance ético.

---

## Licencia

Propietario. Todos los derechos reservados.
