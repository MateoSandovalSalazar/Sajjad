"""Tests de endpoints públicos / de salud."""

import pytest

from tests.conftest import API

pytestmark = pytest.mark.asyncio


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_list_plans_excludes_free(client):
    r = await client.get(f"{API}/billing/plans")
    assert r.status_code == 200
    plans = r.json()
    names = {p["name"] for p in plans}
    assert "free" not in names
    assert {"starter", "professional", "agency"} <= names
    starter = next(p for p in plans if p["name"] == "starter")
    assert starter["price_usd"] == 30
