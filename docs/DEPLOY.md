# Despliegue en producción — VPS + Docker Compose

Guía para poner Sajjad en un servidor. Escrita para un VPS Ubuntu
22.04/24.04 (Hetzner, DigitalOcean, Contabo), que es el destino
correcto para este producto.

## Por qué VPS y no un PaaS

`naabu` y `nmap` hacen SYN scan, que necesita raw sockets
(`CAP_NET_RAW`). Railway, Render y Fly no conceden esa capacidad, así
que en un PaaS habría que degradar a connect-scan —más lento y más
ruidoso— o sacar el worker a una VM aparte de todas formas. Un VPS
con Docker Compose es más simple y más barato.

**Dimensionamiento mínimo:** 2 vCPU / 4 GB RAM / 40 GB disco. Los
escaneos son intensivos en red y en E/S, no en CPU. Con 4 GB corren
holgados la API, el worker (concurrencia 2), Postgres y Redis.

---

## 1. Preparar el servidor

```bash
# Como root en el VPS recién creado
adduser sajjad && usermod -aG sudo sajjad
# Copia tu clave SSH a /home/sajjad/.ssh/authorized_keys

# Endurecer SSH: sin login de root, sin contraseñas
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' \
  /etc/ssh/sshd_config
systemctl restart ssh

# Firewall: sólo SSH y HTTP/S
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

# Actualizaciones de seguridad automáticas
apt update && apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

Instala Docker:

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker sajjad
```

---

## 2. DNS

Apunta un registro `A` de tu dominio a la IP del VPS **antes** de
levantar Caddy — necesita resolver el dominio para obtener el
certificado de Let's Encrypt.

```
sajjad.app.      A     198.51.100.42
www.sajjad.app.  CNAME sajjad.app.
```

---

## 3. Clonar y configurar

```bash
su - sajjad
git clone <tu-repo> sajjad && cd sajjad/backend
cp .env.example .env
```

Edita `backend/.env`. Lo mínimo para arrancar:

```bash
API_ENV=production
API_SECRET_KEY=$(openssl rand -hex 32)   # ¡pégalo, no lo dejes literal!
API_BASE_URL=https://sajjad.app
FRONTEND_URL=https://sajjad.app
ALLOWED_ORIGINS=https://sajjad.app
ALLOWED_HOSTS=sajjad.app,www.sajjad.app

# Postgres — los usa tanto la app como el contenedor de backups
POSTGRES_USER=sajjad
POSTGRES_PASSWORD=<contraseña larga y aleatoria>
POSTGRES_DB=sajjad_db
DATABASE_URL=postgresql+asyncpg://sajjad:<misma-contraseña>@postgres:5432/sajjad_db
REDIS_URL=redis://redis:6379/0

# SMTP real (los emails de verificación son parte del flujo de alta)
SMTP_HOST=smtp.resend.com
SMTP_USER=resend
SMTP_PASSWORD=<api key>
SMTP_FROM=noreply@sajjad.app

# Caddy
SAJJAD_DOMAIN=sajjad.app

# Pagos apagados por ahora
BILLING_ENABLED=false
```

> `API_ENV=production` activa una validación de arranque: si
> `API_SECRET_KEY` sigue siendo el valor por defecto o mide menos de
> 32 caracteres, o si `ALLOWED_ORIGINS` es `*`, la API **no levanta**.
> Es intencional.

---

## 4. Compilar el frontend

Caddy sirve `frontend/dist` como estáticos.

```bash
cd ~/sajjad/frontend
echo "VITE_API_URL=/api/v1" > .env.production
npm ci && npm run build
```

---

## 5. Levantar

```bash
cd ~/sajjad/backend
docker compose -f docker-compose.prod.yml up -d --build
```

El servicio `migrate` aplica las migraciones antes de que arranque la
API (`depends_on: service_completed_successfully`).

Comprobaciones:

```bash
curl -s https://sajjad.app/health          # {"status":"ok",...}
curl -s https://sajjad.app/health/ready    # comprueba Postgres y Redis
docker compose -f docker-compose.prod.yml ps
```

---

## 6. Verificar el endurecimiento

Sajjad es un producto de seguridad: tiene que aprobar su propia
revisión.

```bash
# Cabeceras de seguridad (HSTS, CSP, nosniff, frame-options)
curl -sI https://sajjad.app | grep -i "strict-transport\|content-security"

# La documentación de la API está desactivada en producción
curl -s -o /dev/null -w "%{http_code}\n" https://sajjad.app/docs   # 404

# Postgres y Redis no son alcanzables desde fuera
nmap -Pn -p 5432,6379 sajjad.app   # ambos filtered/closed

# Y, cuando esté todo en marcha, escanéate a ti mismo con Sajjad.
```

---

## 7. Operación

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f worker

# Desplegar una versión nueva
git pull
cd ../frontend && npm ci && npm run build && cd ../backend
docker compose -f docker-compose.prod.yml up -d --build

# Restaurar un backup
gunzip -c backups/sajjad-20260805-030000.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U sajjad sajjad_db
```

### Backups

El servicio `backup` vuelca Postgres a `backend/backups/` cada 24 h y
conserva 14 días. **Eso no es un backup hasta que salga del VPS** —
si el servidor muere, se van las copias con él. Sincroniza el
directorio a almacenamiento externo:

```bash
# En el crontab del usuario sajjad
0 4 * * * rclone sync ~/sajjad/backend/backups remoto:sajjad-backups
```

Prueba la restauración al menos una vez. Un backup sin restauración
probada es una suposición.

---

## 8. Activar los pagos (más adelante)

Cuando la empresa de Delaware esté operativa y MercadoPago (o Stripe)
configurado:

```bash
# backend/.env
MP_ACCESS_TOKEN=APP_USR-...
MP_WEBHOOK_SECRET=...
BILLING_ENABLED=true
```

```bash
docker compose -f docker-compose.prod.yml up -d api
```

En el panel de MercadoPago, configura la URL del webhook como
`https://sajjad.app/api/v1/billing/webhook` y copia la clave secreta a
`MP_WEBHOOK_SECRET`. Sin ese secreto, todo webhook entrante se
rechaza: es el endpoint que otorga planes y nunca se acepta lo que no
se puede verificar.

Prueba primero con credenciales de sandbox (`TEST-...`) y una
suscripción de prueba completa antes de pasar a producción.
