"""
Tests de la verificación de propiedad por DNS TXT.

Este es el camino de onboarding: si falla, el usuario no puede
escanear nada. Todos los fallos de DNS tienen que salir como
DomainNotVerified (400 con mensaje accionable), nunca como 500.

Regresión que motivó el archivo: el `except` apuntaba a
`dns.exception.NXDOMAIN`, que no existe. Evaluar esa cláusula
lanzaba AttributeError, así que CUALQUIER fallo de DNS —incluido
el caso normal de "todavía no añadí el registro"— devolvía 500.
"""

import dns.exception
import dns.resolver
import pytest

from app.core.exceptions import DomainNotVerified
from app.services import domain_verifier as dv

TOKEN = "sajjad-verify-abc12345"


class _FakeRdata:
    def __init__(self, *strings: bytes):
        self.strings = strings


def _raiser(exc: Exception):
    async def _resolve(*args, **kwargs):
        raise exc

    return _resolve


def _answerer(*rdatas: _FakeRdata):
    async def _resolve(*args, **kwargs):
        return list(rdatas)

    return _resolve


@pytest.mark.asyncio
async def test_token_encontrado(monkeypatch):
    monkeypatch.setattr(
        dv._RESOLVER, "resolve", _answerer(_FakeRdata(TOKEN.encode()))
    )
    assert await dv.verify_domain_ownership("ejemplo.com", TOKEN) is True


@pytest.mark.asyncio
async def test_token_entre_otros_txt(monkeypatch):
    """Un dominio real tiene SPF, DKIM y más: hay que encontrarlo igual."""
    monkeypatch.setattr(
        dv._RESOLVER,
        "resolve",
        _answerer(
            _FakeRdata(b"v=spf1 include:_spf.google.com ~all"),
            _FakeRdata(TOKEN.encode()),
        ),
    )
    assert await dv.verify_domain_ownership("ejemplo.com", TOKEN) is True


@pytest.mark.asyncio
async def test_sin_registros_txt(monkeypatch):
    """NoAnswer = el dominio existe pero aún no tiene el TXT."""
    monkeypatch.setattr(
        dv._RESOLVER, "resolve", _raiser(dns.resolver.NoAnswer())
    )
    with pytest.raises(DomainNotVerified) as exc:
        await dv.verify_domain_ownership("ejemplo.com", TOKEN)
    assert TOKEN in str(exc.value)


@pytest.mark.asyncio
async def test_token_distinto(monkeypatch):
    monkeypatch.setattr(
        dv._RESOLVER,
        "resolve",
        _answerer(_FakeRdata(b"sajjad-verify-00000000")),
    )
    with pytest.raises(DomainNotVerified):
        await dv.verify_domain_ownership("ejemplo.com", TOKEN)


@pytest.mark.asyncio
async def test_dominio_inexistente(monkeypatch):
    monkeypatch.setattr(
        dv._RESOLVER, "resolve", _raiser(dns.resolver.NXDOMAIN())
    )
    with pytest.raises(DomainNotVerified) as exc:
        await dv.verify_domain_ownership("no-existe.com", TOKEN)
    assert "no existe" in str(exc.value).lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        dns.exception.Timeout(),
        dns.resolver.LifetimeTimeout(timeout=10.0, errors=[]),
        dns.resolver.NoNameservers(),
        dns.exception.FormError(),
    ],
)
async def test_fallos_de_dns_no_son_500(monkeypatch, error):
    """
    Cualquier excepción de dnspython debe convertirse en
    DomainNotVerified. Si una se escapa, el usuario ve un 500 y no
    sabe qué hacer.
    """
    monkeypatch.setattr(dv._RESOLVER, "resolve", _raiser(error))
    with pytest.raises(DomainNotVerified):
        await dv.verify_domain_ownership("ejemplo.com", TOKEN)


@pytest.mark.asyncio
async def test_txt_no_utf8_no_rompe(monkeypatch):
    """Un TXT con bytes inválidos no debe tumbar la verificación."""
    monkeypatch.setattr(
        dv._RESOLVER,
        "resolve",
        _answerer(_FakeRdata(b"\xff\xfe binario", TOKEN.encode())),
    )
    assert await dv.verify_domain_ownership("ejemplo.com", TOKEN) is True
