"""
Rate limiting de la API.

Vive aquí y no en main.py para que los routers puedan importar el
limiter sin ciclos de importación.

Almacenamiento en Redis, no en memoria: en producción la API corre
con varios workers de uvicorn, y un contador por proceso deja pasar
N veces el límite configurado. Con Redis el límite es global.

Los valores son por IP. No sustituyen a los límites de plan
(core/limits.py), que son por usuario y cuentan uso legítimo; esto
es la defensa contra abuso: fuerza bruta, alta masiva de cuentas y
bombardeo de correos.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    # Detrás de Caddy, uvicorn corre con --proxy-headers, así que
    # request.client.host ya es la IP real del cliente.
    storage_uri=_settings.redis_url,
    strategy="fixed-window",
    enabled=_settings.rate_limit_enabled,
)


# ── Límites por tipo de endpoint ─────────────────────────────
#
# Se nombran en vez de escribirlos sueltos en cada decorador para
# poder razonar sobre ellos de un vistazo y ajustarlos en un sitio.

# Adivinar contraseñas. Suficiente para un humano que se equivoca,
# inútil para un ataque de diccionario.
LOGIN = "10/minute;60/hour"

# Alta de cuentas: frena el registro masivo de cuentas desechables
# para encadenar pruebas gratuitas.
REGISTER = "5/hour"

# Cada petición manda un correo a una dirección que elige quien
# llama: sin límite es un arma de bombardeo contra terceros.
PASSWORD_RESET_REQUEST = "3/hour"

# Mismo perfil de abuso que el reset: cada petición manda un correo a
# una dirección que elige quien llama.
VERIFICATION_RESEND = "3/hour"

# Adivinar tokens de un solo uso (reset y verificación de email).
TOKEN_SUBMIT = "10/hour"

# El access token dura 15 min, así que un cliente legítimo refresca
# ~4 veces por hora. 30 deja margen de sobra para varias pestañas.
REFRESH = "30/hour"

# Lanzar escaneos ya está limitado por plan; esto sólo evita que un
# bucle roto en el cliente martillee la cola de Celery.
SCAN_LAUNCH = "20/hour"
