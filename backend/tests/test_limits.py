"""Tests unitarios de la lógica de límites de plan."""

from datetime import UTC, datetime

from app.core.limits import get_limits, is_new_billing_month


def _dt(year, month, day=1):
    return datetime(year, month, day, tzinfo=UTC)


def test_is_new_billing_month_when_never_reset():
    assert is_new_billing_month(None, _dt(2026, 6)) is True


def test_is_new_billing_month_same_month():
    reset = _dt(2026, 6, 1)
    now = _dt(2026, 6, 28)
    assert is_new_billing_month(reset, now) is False


def test_is_new_billing_month_next_month():
    reset = _dt(2026, 6, 30)
    now = _dt(2026, 7, 1)
    assert is_new_billing_month(reset, now) is True


def test_is_new_billing_month_next_year():
    reset = _dt(2025, 12, 31)
    now = _dt(2026, 1, 1)
    assert is_new_billing_month(reset, now) is True


def test_get_limits_free_defaults():
    free = get_limits("free")
    assert free.max_domains == 1
    assert free.max_scans_per_month == 1
    assert free.can_see_findings is False
    assert free.can_download_pdf is False


def test_get_limits_unknown_plan_falls_back_to_free():
    assert get_limits("does-not-exist") == get_limits("free")


def test_get_limits_agency_white_label():
    agency = get_limits("agency")
    assert agency.white_label is True
    assert agency.max_domains == 10
