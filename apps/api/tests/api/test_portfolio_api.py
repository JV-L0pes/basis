"""HTTP tests for the portfolio and analytics surfaces (seed providers only)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
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

REGISTER = "/api/v1/auth/register"
CLIENTS = "/api/v1/clients"
PORTFOLIOS = "/api/v1/portfolios"
INSTRUMENTS = "/api/v1/instruments"
PASSWORD = "s3nh4-forte"

VALID_TAX_ID = "52998224725"


def _offline_settings(test_settings: Settings) -> Settings:
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
            "currency": seed.currency_code,
            "mic": None,
            "isin": None,
            "cfi": None,
            "is_active": True,
        }
        for seed in SEED_INSTRUMENTS
    ]
    engine = create_engine(db_url, poolclass=NullPool)
    try:
        with engine.begin() as connection:
            connection.execute(insert(InstrumentRow), rows)
    finally:
        engine.dispose()


@pytest.fixture
def client(test_settings: Settings, db_url: str, schema: None) -> Iterator[TestClient]:
    app: FastAPI = create_app(_offline_settings(test_settings))
    _insert_instruments(db_url)
    with TestClient(app) as test_client:
        yield test_client


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        REGISTER,
        json={
            "email": "ana@basis.dev",
            "password": PASSWORD,
            "display_name": "Ana Souza",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['token']['access_token']}"}


def _open_portfolio(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    client_response = client.post(
        CLIENTS,
        headers=headers,
        json={
            "name": "Ana Souza",
            "email": "ana@basis.dev",
            "tax_id": VALID_TAX_ID,
            "suitability_answers": [4, 4, 3, 4, 4],
        },
    )
    assert client_response.status_code == 201, client_response.text
    portfolio_response = client.post(
        PORTFOLIOS,
        headers=headers,
        json={
            "client_id": client_response.json()["id"],
            "name": "Carteira Ana",
            "base_currency": "BRL",
        },
    )
    assert portfolio_response.status_code == 201, portfolio_response.text
    return portfolio_response.json()


def _record(
    client: TestClient,
    headers: dict[str, str],
    portfolio_id: str,
    *,
    symbol: str,
    quantity: str,
    price: str,
    kind: str = "buy",
    fees: str | None = "4.90",
) -> dict[str, Any]:
    response = client.post(
        f"{PORTFOLIOS}/{portfolio_id}/transactions",
        headers=headers,
        json={
            "symbol": symbol,
            "kind": kind,
            "trade_date": (date.today() - timedelta(days=365)).isoformat(),
            "quantity": quantity,
            "price": price,
            "fees": fees,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestPortfolioFlow:
    def test_portfolio_is_created_for_an_existing_client(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)

        assert portfolio["status"] == "active"
        assert portfolio["transaction_count"] == 0
        assert portfolio["position_count"] == 0

    def test_unknown_client_is_rejected(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        response = client.post(
            PORTFOLIOS,
            headers=headers,
            json={
                "client_id": "01920000-0000-7000-8000-00000000dead",
                "name": "Fantasma",
                "base_currency": "BRL",
            },
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    def test_transactions_build_positions_and_realized_gain(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)

        _record(client, headers, portfolio["id"], symbol="PETR4", quantity="100", price="10.00")
        _record(client, headers, portfolio["id"], symbol="PETR4", quantity="100", price="20.00")
        _record(
            client,
            headers,
            portfolio["id"],
            symbol="PETR4",
            kind="dividend",
            quantity="1",
            price="50.00",
            fees="0",
        )

        detail = client.get(f"{PORTFOLIOS}/{portfolio['id']}", headers=headers).json()
        position = detail["valuation"]["positions"][0]
        assert position["symbol"] == "PETR4"
        assert position["quantity"] == "200"
        # custo medio ponderado das duas compras, taxas incluidas, arredondado ao centavo
        assert position["average_cost"] == "15.05"
        assert detail["valuation"]["income"] == "50.00"

    def test_selling_more_than_held_returns_invariant_violation(
        self, client: TestClient
    ) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)
        _record(client, headers, portfolio["id"], symbol="VALE3", quantity="10", price="60.00")

        response = client.post(
            f"{PORTFOLIOS}/{portfolio['id']}/transactions",
            headers=headers,
            json={
                "symbol": "VALE3",
                "kind": "sell",
                "trade_date": date.today().isoformat(),
                "quantity": "11",
                "price": "61.00",
            },
        )
        assert response.status_code == 422
        assert response.json()["code"] == "invariant_violation"

    def test_future_trade_date_is_rejected(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)
        response = client.post(
            f"{PORTFOLIOS}/{portfolio['id']}/transactions",
            headers=headers,
            json={
                "symbol": "PETR4",
                "kind": "buy",
                "trade_date": (date.today() + timedelta(days=1)).isoformat(),
                "quantity": "1",
                "price": "10.00",
            },
        )
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"

    def test_unknown_instrument_is_rejected(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)
        response = client.post(
            f"{PORTFOLIOS}/{portfolio['id']}/transactions",
            headers=headers,
            json={
                "symbol": "NAOEXISTE",
                "kind": "buy",
                "trade_date": date.today().isoformat(),
                "quantity": "1",
                "price": "10.00",
            },
        )
        assert response.status_code == 404


class TestPortfolioQueries:
    def test_list_marks_every_portfolio_to_market(self, client: TestClient) -> None:
        """RN-24: the list values the page with a single batch of quotes."""
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)
        _record(client, headers, portfolio["id"], symbol="PETR4", quantity="100", price="10.00")

        response = client.get(f"{PORTFOLIOS}?limit=10", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["next_cursor"] is None
        item = body["items"][0]
        assert item["valuation"] is not None
        # 100 acoes a 10.00 com 4.90 de taxa: custo medio 10.049 -> 10.05, base 1005.00
        assert item["valuation"]["invested"] == "1005.00"
        assert item["valuation"]["market_value"] is not None
        assert item["position_count"] == 1

    def test_ledger_is_returned_oldest_first(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)
        _record(client, headers, portfolio["id"], symbol="PETR4", quantity="10", price="10.00")
        _record(client, headers, portfolio["id"], symbol="VALE3", quantity="5", price="60.00")

        response = client.get(f"{PORTFOLIOS}/{portfolio['id']}/transactions", headers=headers)

        assert response.status_code == 200
        assert [item["symbol"] for item in response.json()] == ["PETR4", "VALE3"]

    def test_targets_must_sum_to_one_hundred_percent(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)

        response = client.put(
            f"{PORTFOLIOS}/{portfolio['id']}/targets",
            headers=headers,
            json={"targets": [{"asset_class": "equity", "weight_bps": 6000}]},
        )

        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"

    def test_targets_are_accepted_and_drive_the_drift(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)
        _record(client, headers, portfolio["id"], symbol="PETR4", quantity="100", price="10.00")

        updated = client.put(
            f"{PORTFOLIOS}/{portfolio['id']}/targets",
            headers=headers,
            json={
                "targets": [
                    {"asset_class": "equity", "weight_bps": 6000},
                    {"asset_class": "fixed_income", "weight_bps": 4000},
                ]
            },
        )
        assert updated.status_code == 200, updated.text
        assert len(updated.json()["targets"]) == 2

        analysis = client.get(
            f"/api/v1/analytics/portfolios/{portfolio['id']}/allocation", headers=headers
        ).json()
        assert analysis["has_targets"] is True
        drift = {item["asset_class"]: item["drift_bps"] for item in analysis["drift"]}
        assert drift["equity"] == 4000
        assert drift["fixed_income"] == -4000
        assert analysis["plan"][0]["action"] in {"sell", "buy"}


class TestAnalytics:
    def test_performance_reports_twr_and_risk_metrics(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)
        _record(client, headers, portfolio["id"], symbol="PETR4", quantity="100", price="10.00")

        response = client.get(
            f"/api/v1/analytics/portfolios/{portfolio['id']}/performance", headers=headers
        )

        assert response.status_code == 200, response.text
        report = response.json()
        assert report["twr"] is not None
        assert report["xirr"] is not None
        assert report["max_drawdown"] is not None
        assert len(report["equity_curve"]) >= 1
        # the risk-free rate is an annualised Selic, never an extrapolated total
        assert 0 < report["risk_free_annual"] < 0.5

    def test_book_overview_aggregates_every_portfolio(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        portfolio = _open_portfolio(client, headers)
        _record(client, headers, portfolio["id"], symbol="PETR4", quantity="100", price="10.00")

        response = client.get("/api/v1/analytics/book", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["portfolio_count"] == 1
        assert body["total_market_value"] != "0.00"
        assert body["allocation"][0]["asset_class"] == "equity"


class TestCatalog:
    def test_seeded_instruments_are_available(self, client: TestClient) -> None:
        headers = _auth_headers(client)
        response = client.get(f"{INSTRUMENTS}?limit=50", headers=headers)
        assert response.status_code == 200
        symbols = {item["symbol"] for item in response.json()["items"]}
        assert {"PETR4", "BTC", "TESOURO2029", "CDB2027"} <= symbols
