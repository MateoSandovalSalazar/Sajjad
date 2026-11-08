"""
Tests unitarios del servicio Mercado Pago: verificación de firma
HMAC del webhook y parseo de eventos. No tocan red (puro cómputo).
"""

import hashlib
import hmac
import time
from types import SimpleNamespace

from app.services import mercadopago as mp


def _sign(secret: str, data_id: str, request_id: str, ts: str) -> str:
    """Reproduce el manifest exacto que firma Mercado Pago."""
    manifest = (
        f"id:{data_id};request-id:{request_id};ts:{ts};"
    )
    return hmac.new(
        secret.encode(), manifest.encode(), hashlib.sha256
    ).hexdigest()


def _now_ts() -> str:
    return str(int(time.time()))


def _fake_settings(secret: str):
    return SimpleNamespace(mp_webhook_secret=secret)


def test_verify_signature_valid(monkeypatch):
    secret = "supersecret"
    monkeypatch.setattr(
        mp, "get_settings", lambda: _fake_settings(secret)
    )
    data_id, rid, ts = "preapp-1", "req-123", _now_ts()
    v1 = _sign(secret, data_id, rid, ts)
    header = f"ts={ts},v1={v1}"

    assert mp.verify_webhook_signature(header, rid, data_id) is True


def test_verify_signature_normalizes_data_id_case(monkeypatch):
    """MP pasa el data.id a minúsculas antes de firmar."""
    secret = "supersecret"
    monkeypatch.setattr(
        mp, "get_settings", lambda: _fake_settings(secret)
    )
    rid, ts = "req-123", _now_ts()
    v1 = _sign(secret, "abc123", rid, ts)
    header = f"ts={ts},v1={v1}"

    assert mp.verify_webhook_signature(header, rid, "ABC123") is True


def test_verify_signature_wrong_data_id(monkeypatch):
    """La firma va atada al data.id: otro id no valida."""
    secret = "supersecret"
    monkeypatch.setattr(
        mp, "get_settings", lambda: _fake_settings(secret)
    )
    rid, ts = "req-123", _now_ts()
    v1 = _sign(secret, "preapp-1", rid, ts)
    header = f"ts={ts},v1={v1}"

    assert (
        mp.verify_webhook_signature(header, rid, "preapp-OTRO") is False
    )


def test_verify_signature_rejects_stale_timestamp(monkeypatch):
    """Un webhook capturado no puede reenviarse horas después."""
    secret = "supersecret"
    monkeypatch.setattr(
        mp, "get_settings", lambda: _fake_settings(secret)
    )
    data_id, rid = "preapp-1", "req-123"
    old_ts = str(int(time.time()) - 3600)
    v1 = _sign(secret, data_id, rid, old_ts)
    header = f"ts={old_ts},v1={v1}"

    assert mp.verify_webhook_signature(header, rid, data_id) is False


def test_verify_signature_invalid(monkeypatch):
    monkeypatch.setattr(
        mp, "get_settings", lambda: _fake_settings("supersecret")
    )
    header = f"ts={_now_ts()},v1=deadbeef"
    assert (
        mp.verify_webhook_signature(header, "req-123", "preapp-1")
        is False
    )


def test_verify_signature_missing_header(monkeypatch):
    monkeypatch.setattr(
        mp, "get_settings", lambda: _fake_settings("supersecret")
    )
    assert (
        mp.verify_webhook_signature(None, "req-123", "preapp-1")
        is False
    )


def test_verify_signature_fails_closed_without_secret(monkeypatch):
    """
    Sin MP_WEBHOOK_SECRET se rechaza TODO.

    Este endpoint otorga planes: aceptar sin poder verificar el origen
    dejaría que cualquiera se auto-asigne el plan Agency con un POST.
    """
    monkeypatch.setattr(
        mp, "get_settings", lambda: _fake_settings("")
    )
    assert mp.verify_webhook_signature(None, None, None) is False

    # Ni siquiera con una cabecera bien formada.
    ts = _now_ts()
    v1 = _sign("", "preapp-1", "req-1", ts)
    assert (
        mp.verify_webhook_signature(
            f"ts={ts},v1={v1}", "req-1", "preapp-1"
        )
        is False
    )


def test_parse_subscription_event():
    payload = {
        "type": "subscription_preapproval",
        "action": "updated",
        "data": {"id": "preapp-1"},
    }
    event = mp.parse_webhook_event(payload)
    assert event == {
        "kind": "subscription",
        "action": "updated",
        "preapproval_id": "preapp-1",
    }


def test_parse_payment_event():
    payload = {
        "type": "payment",
        "action": "created",
        "data": {"id": "pay-9"},
    }
    event = mp.parse_webhook_event(payload)
    assert event["kind"] == "payment"
    assert event["payment_id"] == "pay-9"


def test_parse_unknown_event_returns_none():
    assert mp.parse_webhook_event({"type": "topic_merchant"}) is None
