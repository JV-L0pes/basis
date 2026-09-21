"""HTTP tests for the market-data surface (seed providers only, no network)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.pool import NullPool

from basis.config import MarketDataSettings, Settings
from basis.kernel.domain.identifiers import new_id
from basis.main import create_app
from basis.modules.market_data.infrastructure.models import InstrumentRow
from basis.modules.market_data.infrastructure.providers.seed import SEED_INSTRUMENTS
from basis.modules.market_data.presentation.dependencies import build_market_data_runtime
from basis.modules.market_data.presentation.router import router as market_router

REGISTER = "/api/v1/auth/register"
INSTRUMENTS = "/api/v1/instruments"
OVERVIEW = "/api/v1/market/overview"
PASSWORD = "s3nh4-forte"


def _market_settings(test_settings: Settings) -> Settings:
    return test_settings.model_copy(
        update={"market_data": MarketDataSettings(allow_live_providers=False)}
    )


def _insert_instruments(db_url: str) -> None:
    rows: list[dict[str, Any]] = [
        {
            "id": new_id(),
            "symbol": seed.symbol,
            "name": seed.name,
            "asset_class": seed.asset_class.value,
            "currency": "BRL",
            "mic": None,
            "isin": None,
            "cfi": None,
            "is_active": True,
        }
        for seed in SEED_INSTRUMENTS
    ]
    rows.append(
        {
            "id": new_id(),
            "symbol": "XPTO3",
            "name": "Sem Preco S.A.",
            "asset_class": "equity",
            "currency": "BRL",
            "mic": None,
            "isin": None,
            "cfi": None,
            "is_active": True,
        }
    )
    engine = create_engine(db_url, poolclass=NullPool)
    try:
        with engine.begin() as connection:
            connection.execute(insert(InstrumentRow), rows)
    finally:
        engine.dispose()


@pytest.fixture
def client(test_settings: Settings, db_url: str) -> Iterator[TestClient]:
    """App with the market router mounted and deterministic seed providers."""
    settings = _market_settings(test_settings)
    app: FastAPI = create_app(settings)
    app.include_router(market_router, prefix="/api/v1")
    app.state.market_data_runtime = build_market_data_runtime(settings)
    _insert_instruments(db_url)
    with TestClient(app) as test_client:
        yield test_client


def _register(client: TestClient) -> dict[str, str]:
    response = client.post(
        REGISTER,
        json={"email": "ana@basis.dev", "password": PASSWORD, "display_name": "Ana Souza"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['token']['access_token']}"}


class TestInstrumentsApi:
    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.get(INSTRUMENTS)
        assert response.status_code == 401
        assert response.json()["code"] == "unauthenticated"

    def test_lists_the_seeded_catalogue(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(INSTRUMENTS, headers=headers)
        assert response.status_code == 200
        body = response.json()
        symbols = [item["symbol"] for item in body["items"]]
        assert "PETR4" in symbols
        assert "BTC" in symbols
        assert body["next_cursor"] is None
        petr = next(item for item in body["items"] if item["symbol"] == "PETR4")
        assert petr["asset_class"] == "equity"
        assert petr["currency"] == "BRL"
        assert petr["is_active"] is True

    def test_filters_by_asset_class_and_query(self, client: TestClient) -> None:
        headers = _register(client)
        crypto = client.get(INSTRUMENTS, params={"asset_class": "crypto"}, headers=headers).json()
        assert [item["symbol"] for item in crypto["items"]] == ["BTC", "ETH"]

        filtered = client.get(INSTRUMENTS, params={"query": "vale"}, headers=headers).json()
        assert [item["symbol"] for item in filtered["items"]] == ["VALE3"]

    def test_paginates_with_a_cursor(self, client: TestClient) -> None:
        headers = _register(client)
        first = client.get(INSTRUMENTS, params={"limit": 5}, headers=headers).json()
        assert len(first["items"]) == 5
        assert first["next_cursor"] is not None

        second = client.get(
            INSTRUMENTS,
            params={"limit": 5, "cursor": first["next_cursor"]},
            headers=headers,
        ).json()
        assert second["items"]
        assert first["items"][-1]["symbol"] < second["items"][0]["symbol"]

    def test_get_by_symbol(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(f"{INSTRUMENTS}/petr4", headers=headers)
        assert response.status_code == 200
        assert response.json()["symbol"] == "PETR4"

    def test_unknown_symbol_returns_problem_details(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(f"{INSTRUMENTS}/NAOEXISTE", headers=headers)
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"


class TestQuotesApi:
    def test_returns_a_seed_quote(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(f"{INSTRUMENTS}/PETR4/quote", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "PETR4"
        assert body["price"] == "38.72"
        assert body["source"] == "seed"
        assert body["change_percent"] is not None
        assert body["as_of"]

    def test_quote_without_seed_price_returns_404(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(f"{INSTRUMENTS}/XPTO3/quote", headers=headers)
        assert response.status_code == 404

    def test_history_covers_the_requested_window(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(
            f"{INSTRUMENTS}/PETR4/history",
            params={"start": "2026-06-01", "end": "2026-06-05"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert [point["date"] for point in body] == [
            "2026-06-01",
            "2026-06-02",
            "2026-06-03",
            "2026-06-04",
            "2026-06-05",
        ]
        assert body[-1]["close"] == "38.72"
        assert body[0]["currency"] == "BRL"

    def test_history_defaults_to_the_last_ninety_days(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(f"{INSTRUMENTS}/PETR4/history", headers=headers)
        assert response.status_code == 200
        body = response.json()
        first, last = date.fromisoformat(body[0]["date"]), date.fromisoformat(body[-1]["date"])
        assert (last - first).days == 90


class TestMacroApi:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get("/api/v1/market/macro/selic").status_code == 401

    def test_returns_the_requested_series(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(
            "/api/v1/market/macro/selic",
            params={"start": "2026-05-01", "end": "2026-05-10"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 10
        assert body[0]["code"] == "selic"
        assert body[0]["date"] == "2026-05-01"
        assert body[-1]["value"]

    def test_unknown_code_is_rejected(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get("/api/v1/market/macro/desconhecido", headers=headers)
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"


class TestOverviewApi:
    def test_returns_macro_and_blue_chip_quotes(self, client: TestClient) -> None:
        headers = _register(client)
        response = client.get(OVERVIEW, headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert {point["code"] for point in body["macro"]} == {
            "selic",
            "cdi",
            "ipca",
            "usd_brl",
        }
        assert len(body["quotes"]) == 12
        assert all(quote["source"] == "seed" for quote in body["quotes"])
