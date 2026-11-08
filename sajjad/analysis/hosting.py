"""
Detección de infraestructura compartida (CDN / PaaS / SaaS).

Por qué existe este módulo
--------------------------
Cuando un dominio está en Vercel, Netlify, Cloudflare o Shopify, sus
registros A apuntan a IPs que NO pertenecen al cliente: son la red
compartida del proveedor, la misma para millones de sitios.

Escanear puertos contra esas IPs es un problema por tres motivos:

1. **Alcance.** El cliente puede autorizar el análisis de SU dominio,
   pero no el de la infraestructura de Vercel. La verificación DNS
   TXT demuestra control del dominio, no propiedad de la IP. Es
   exactamente el límite que Sajjad no cruza.

2. **Utilidad.** Los puertos abiertos serían los del edge del
   proveedor, idénticos para cualquier otro cliente suyo. No dicen
   nada sobre la seguridad del cliente y ensucian el informe con
   hallazgos que no puede remediar.

3. **Operativa.** Escanear rangos de un CDN suele infringir sus
   términos de servicio y acaba con la IP del escáner bloqueada.

Qué hace en su lugar
--------------------
Las etapas que SÍ son informativas para un sitio en PaaS —HTTP,
cabeceras de seguridad, TLS, DNS de correo, nuclei— se ejecutan con
normalidad. Sólo se omite el escaneo de puertos, y se emite un
hallazgo informativo explicando por qué.

Estrategia de detección
-----------------------
Se prioriza lo que NO caduca (nameservers y CNAME, que el proveedor
controla y rara vez cambia de forma) sobre las listas de rangos IP,
que envejecen mal. Los rangos son sólo un respaldo, y para los
proveedores cuyos bloques son estables y bien conocidos.
"""

import ipaddress
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HostingProvider:
    name: str
    # Fragmentos que aparecen en el nombre de los nameservers o en el
    # destino de un CNAME. Es la señal más estable.
    dns_markers: tuple[str, ...]
    # Rangos IP conocidos. Respaldo: pueden quedar desactualizados.
    ip_ranges: tuple[str, ...] = field(default=())


PROVIDERS: tuple[HostingProvider, ...] = (
    HostingProvider(
        name="Vercel",
        dns_markers=("vercel-dns.com", "vercel.app", "vercel.com"),
        ip_ranges=("76.76.21.0/24", "64.29.17.0/24", "216.198.79.0/24"),
    ),
    HostingProvider(
        name="Cloudflare",
        dns_markers=("cloudflare.com", "cloudflare.net"),
        ip_ranges=(
            "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13",
            "162.158.0.0/15", "173.245.48.0/20", "103.21.244.0/22",
            "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20",
            "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17",
        ),
    ),
    HostingProvider(
        name="Netlify",
        dns_markers=("nsone.net", "netlify.com", "netlify.app"),
        ip_ranges=("75.2.60.0/24", "99.83.190.0/24"),
    ),
    HostingProvider(
        name="Shopify",
        dns_markers=("shopify.com", "myshopify.com"),
        ip_ranges=("23.227.38.0/24",),
    ),
    HostingProvider(
        name="AWS CloudFront",
        dns_markers=("cloudfront.net", "awsdns"),
    ),
    HostingProvider(
        name="Fastly",
        dns_markers=("fastly.net", "fastlylb.net"),
        ip_ranges=("151.101.0.0/16", "199.232.0.0/16"),
    ),
    HostingProvider(
        name="GitHub Pages",
        dns_markers=("github.io", "githubusercontent"),
        ip_ranges=("185.199.108.0/22",),
    ),
    HostingProvider(
        name="Wix",
        dns_markers=("wixdns.net", "wix.com"),
    ),
    HostingProvider(
        name="Squarespace",
        dns_markers=("squarespace.com", "sqspcdn.com"),
    ),
    HostingProvider(
        name="Akamai",
        dns_markers=("akam.net", "akamaiedge.net", "akamai.net"),
    ),
)


def _networks(provider: HostingProvider):
    for cidr in provider.ip_ranges:
        try:
            yield ipaddress.ip_network(cidr)
        except ValueError:  # pragma: no cover - rangos mal escritos
            logger.warning("Rango inválido en %s: %s", provider.name, cidr)


def provider_for_ip(ip: str) -> str | None:
    """Nombre del proveedor cuyo rango contiene la IP, o None."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None

    for provider in PROVIDERS:
        for net in _networks(provider):
            if addr in net:
                return provider.name
    return None


def provider_for_dns(names: list[str]) -> str | None:
    """
    Nombre del proveedor a partir de nameservers o destinos CNAME.

    Es la señal preferente: un proveedor puede rotar sus IPs sin
    avisar, pero no el dominio de sus nameservers.
    """
    haystack = " ".join(n.lower() for n in names if n)
    for provider in PROVIDERS:
        if any(marker in haystack for marker in provider.dns_markers):
            return provider.name
    return None


def detect_provider(
    ips: list[str] | None = None,
    dns_names: list[str] | None = None,
) -> str | None:
    """
    Identifica el proveedor de hosting compartido, si lo hay.

    Se consulta primero el DNS porque es la señal estable; los rangos
    IP se usan sólo si el DNS no dice nada.
    """
    if dns_names:
        found = provider_for_dns(dns_names)
        if found:
            return found

    for ip in ips or []:
        found = provider_for_ip(ip)
        if found:
            return found

    return None


def is_shared_infrastructure(
    ips: list[str] | None = None,
    dns_names: list[str] | None = None,
) -> bool:
    return detect_provider(ips, dns_names) is not None


def classify_hosts(
    dns_records: list[dict],
) -> tuple[list[str], dict[str, str]]:
    """
    Separa los hosts propios de los que viven en un CDN o PaaS.

    La decisión es POR HOST, no por dominio: que la raíz esté en
    Vercel no significa que `erp.midominio.com` también lo esté. Ese
    subdominio puede apuntar a un servidor del cliente, y es
    justamente donde suelen estar los problemas graves — omitirlo
    por lo que hace la raíz sería dejar de mirar lo que más importa.

    Devuelve:
        (hosts_propios, {host: proveedor})
    """
    own: list[str] = []
    shared: dict[str, str] = {}

    for record in dns_records:
        host = record.get("host")
        if not host:
            continue

        cname = record.get("cname")
        cnames = cname if isinstance(cname, list) else [cname] if cname else []

        provider = detect_provider(
            ips=record.get("a") or [],
            dns_names=cnames,
        )

        if provider:
            shared[host] = provider
        elif host not in own:
            own.append(host)

    return own, shared
