"""
DNS TXT ownership verification.

The client adds a TXT record like:
    sajjad-verify-abc12345

We query DNS and check if that token appears in any TXT
record for the root domain. Verification is idempotent
and can be retried any number of times.
"""

import logging

import dns.asyncresolver
import dns.exception
import dns.resolver

from app.core.exceptions import DomainNotVerified

logger = logging.getLogger(__name__)

_RESOLVER = dns.asyncresolver.Resolver()
_RESOLVER.timeout = 5
_RESOLVER.lifetime = 10


async def verify_domain_ownership(
    fqdn: str,
    expected_token: str,
) -> bool:
    """
    Returns True if the TXT record with `expected_token` is
    found in DNS. Raises DomainNotVerified on failure.
    """
    txt_records = await _fetch_txt_records(fqdn)

    for record in txt_records:
        if expected_token in record:
            logger.info(
                "Domain %s verified with token %s",
                fqdn,
                expected_token,
            )
            return True

    raise DomainNotVerified(
        f"No se encontró el token '{expected_token}' en los registros "
        f"TXT de '{fqdn}'. Añade el registro TXT en la raíz del "
        f"dominio y vuelve a intentarlo."
    )


async def _fetch_txt_records(fqdn: str) -> list[str]:
    try:
        answers = await _RESOLVER.resolve(fqdn, "TXT")
        records = []
        for rdata in answers:
            for string in rdata.strings:
                decoded = (
                    string.decode("utf-8", errors="ignore")
                    if isinstance(string, bytes)
                    else str(string)
                )
                records.append(decoded)
        return records
    except dns.resolver.NXDOMAIN:
        # OJO: NXDOMAIN vive en dns.resolver, no en dns.exception.
        # Apuntar al módulo equivocado hacía que evaluar esta cláusula
        # lanzara AttributeError, y TODO fallo de DNS terminaba en un
        # 500 en vez del mensaje de "añade el registro TXT".
        raise DomainNotVerified(
            f"El dominio '{fqdn}' no existe en el DNS. "
            f"Revisa que esté bien escrito."
        )
    except dns.resolver.NoAnswer:
        # El dominio existe pero no tiene ningún TXT: es el caso normal
        # de quien aún no ha añadido el registro.
        return []
    except (
        dns.exception.Timeout,
        dns.resolver.NoNameservers,
        dns.resolver.LifetimeTimeout,
    ) as exc:
        logger.warning("Consulta DNS fallida para %s: %s", fqdn, exc)
        raise DomainNotVerified(
            f"No se pudo consultar el DNS de '{fqdn}'. "
            f"Inténtalo de nuevo en unos minutos."
        )
    except dns.exception.DNSException as exc:
        # Red de seguridad: cualquier otro fallo de dnspython es un
        # problema de DNS del usuario, no un error interno nuestro.
        logger.warning("Error de DNS inesperado para %s: %s", fqdn, exc)
        raise DomainNotVerified(
            f"No se pudo verificar '{fqdn}' por un problema de DNS. "
            f"Inténtalo de nuevo en unos minutos."
        )
