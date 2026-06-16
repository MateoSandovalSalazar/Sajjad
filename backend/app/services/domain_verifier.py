"""
DNS TXT ownership verification.

The client adds a TXT record like:
    sajjad-verify-abc12345

We query DNS and check if that token appears in any TXT
record for the root domain. Verification is idempotent
and can be retried any number of times.
"""

import asyncio
import logging

import dns.asyncresolver
import dns.exception

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
        f"Token '{expected_token}' not found in TXT records for "
        f"'{fqdn}'. Add the TXT record and try again."
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
    except dns.exception.NXDOMAIN:
        raise DomainNotVerified(
            f"Domain '{fqdn}' does not exist in DNS."
        )
    except (
        dns.exception.Timeout,
        dns.resolver.NoNameservers,
    ) as exc:
        logger.warning(
            "DNS lookup failed for %s: %s", fqdn, exc
        )
        raise DomainNotVerified(
            f"Could not reach DNS for '{fqdn}'. Try again later."
        )
    except dns.resolver.NoAnswer:
        return []
