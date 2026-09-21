"""HTTP tests for the clients surface.

The application factory is overridden locally to mount the clients router;
``basis.api`` (owned by the composition root) is intentionally untouched.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from basis.config import Settings
from basis.main import create_app
from basis.modules.clients.presentation.router import router as clients_router

CLIENTS = "/api/v1/clients"
REGISTER_USER = "/api/v1/auth/register"

PASSWORD = "s3nh4-forte"

CPF = "52998224725"
CNPJ = "11222333000181"

TAX_IDS = ["52998224725", "11144477735", "12345678909", "39053344705", "86288366757"]


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    application = create_app(test_settings)
    application.include_router(clients_router, prefix="/api/v1")
    return application


def register_user(client: TestClient, email: str = "ana@basis.dev") -> str:
    response = client.post(
        REGISTER_USER,
        json={"email": email, "password": PASSWORD, "display_name": "Ana Souza"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["token"]["access_token"])


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_client(client: TestClient, token: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Ana Souza",
        "email": "ana.souza@example.com",
        "tax_id": CPF,
        "notes": "Private banking",
        "suitability_answers": [4, 4, 3, 4, 4],
    }
    payload.update(overrides)
    response = client.post(CLIENTS, json=payload, headers=bearer(token))
    assert response.status_code == 201, response.text
    return dict(response.json())


class TestAuthentication:
    def test_list_requires_a_bearer_token(self, client: TestClient) -> None:
        response = client.get(CLIENTS)
        assert response.status_code == 401
        assert response.json()["code"] == "unauthenticated"

    def test_create_requires_a_bearer_token(self, client: TestClient) -> None:
        response = client.post(
            CLIENTS,
            json={"name": "Ana Souza", "email": "ana@example.com", "tax_id": CPF},
        )
        assert response.status_code == 401
        assert response.json()["code"] == "unauthenticated"


class TestRegisterClient:
    def test_creates_a_client_with_masked_tax_id(self, client: TestClient) -> None:
        token = register_user(client)
        body = create_client(client, token)

        assert body["tax_id_masked"] == "***.***.247-25"
        assert body["status"] == "active"
        assert body["suitability"] == "aggressive"
        assert body["suitability_score"] == 95
        assert body["notes"] == "Private banking"

    def test_accepts_a_formatted_cnpj(self, client: TestClient) -> None:
        token = register_user(client)
        body = create_client(
            client, token, tax_id="11.222.333/0001-81", email="empresa@example.com"
        )
        assert body["tax_id_masked"] == "**.***.***/****-81"

    def test_omitted_answers_default_to_a_neutral_assessment(self, client: TestClient) -> None:
        token = register_user(client)
        body = create_client(client, token, suitability_answers=None)
        assert body["suitability"] == "moderate"
        assert body["suitability_score"] == 50

    def test_duplicate_tax_id_conflicts(self, client: TestClient) -> None:
        token = register_user(client)
        create_client(client, token)

        response = client.post(
            CLIENTS,
            json={"name": "Outra Pessoa", "email": "outra@example.com", "tax_id": CPF},
            headers=bearer(token),
        )

        assert response.status_code == 409
        problem = response.json()
        assert problem["code"] == "conflict"
        assert response.headers["content-type"].startswith("application/problem+json")

    def test_invalid_cpf_is_rejected(self, client: TestClient) -> None:
        token = register_user(client)
        response = client.post(
            CLIENTS,
            json={
                "name": "Ana Souza",
                "email": "ana@example.com",
                "tax_id": "52998224724",
            },
            headers=bearer(token),
        )

        assert response.status_code == 422
        problem = response.json()
        assert problem["code"] == "validation_error"
        assert problem["errors"][0]["detail"]["value"] == "52998224724"

    def test_invalid_cnpj_is_rejected(self, client: TestClient) -> None:
        token = register_user(client)
        response = client.post(
            CLIENTS,
            json={
                "name": "Empresa Ltda",
                "email": "contato@empresa.com",
                "tax_id": "11.222.333/0001-82",
            },
            headers=bearer(token),
        )
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"

    def test_out_of_range_answers_are_rejected(self, client: TestClient) -> None:
        token = register_user(client)
        response = client.post(
            CLIENTS,
            json={
                "name": "Ana Souza",
                "email": "ana@example.com",
                "tax_id": CPF,
                "suitability_answers": [4, 4, 9, 4, 4],
            },
            headers=bearer(token),
        )
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"


class TestClientLifecycle:
    def test_get_update_assess_archive_and_reactivate(self, client: TestClient) -> None:
        token = register_user(client)
        created = create_client(client, token)
        client_id = created["id"]
        headers = bearer(token)

        fetched = client.get(f"{CLIENTS}/{client_id}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Ana Souza"

        updated = client.patch(
            f"{CLIENTS}/{client_id}",
            json={"name": "Ana Maria Souza", "notes": "Updated"},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Ana Maria Souza"
        assert updated.json()["email"] == "ana.souza@example.com"

        assessed = client.post(
            f"{CLIENTS}/{client_id}/suitability",
            json={"answers": [0, 0, 0, 0, 0]},
            headers=headers,
        )
        assert assessed.status_code == 200
        assert assessed.json() == {"score": 0, "profile": "conservative"}

        archived = client.post(f"{CLIENTS}/{client_id}/archive", headers=headers)
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"

        blocked = client.patch(
            f"{CLIENTS}/{client_id}", json={"name": "Outro Nome"}, headers=headers
        )
        assert blocked.status_code == 422
        assert blocked.json()["code"] == "invariant_violation"

        blocked_assessment = client.post(
            f"{CLIENTS}/{client_id}/suitability",
            json={"answers": [4, 4, 4, 4, 4]},
            headers=headers,
        )
        assert blocked_assessment.status_code == 422

        reactivated = client.post(f"{CLIENTS}/{client_id}/reactivate", headers=headers)
        assert reactivated.status_code == 200
        assert reactivated.json()["status"] == "active"

        after_reactivation = client.patch(
            f"{CLIENTS}/{client_id}", json={"name": "Ana Souza"}, headers=headers
        )
        assert after_reactivation.status_code == 200

    def test_unknown_client_returns_404(self, client: TestClient) -> None:
        token = register_user(client)
        response = client.get(
            f"{CLIENTS}/00000000-0000-7000-8000-000000000000", headers=bearer(token)
        )
        assert response.status_code == 404
        problem = response.json()
        assert problem["code"] == "not_found"
        assert problem["status"] == 404

    def test_unknown_client_cannot_be_archived(self, client: TestClient) -> None:
        token = register_user(client)
        response = client.post(
            f"{CLIENTS}/00000000-0000-7000-8000-000000000000/archive",
            headers=bearer(token),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"


class TestListClients:
    def test_paginates_and_filters(self, client: TestClient) -> None:
        token = register_user(client)
        headers = bearer(token)
        names = [
            "Alice Prado",
            "Bruno Lima",
            "Carla Dias",
            "Diego Alves",
            "Elisa Moraes",
        ]
        for name, tax_id in zip(names, TAX_IDS, strict=True):
            create_client(
                client,
                token,
                name=name,
                email=f"{name.split()[0].lower()}@example.com",
                tax_id=tax_id,
            )

        first = client.get(CLIENTS, params={"limit": 2}, headers=headers)
        assert first.status_code == 200
        first_body = first.json()
        assert len(first_body["items"]) == 2
        assert first_body["next_cursor"] is not None

        second = client.get(
            CLIENTS,
            params={"limit": 2, "cursor": first_body["next_cursor"]},
            headers=headers,
        )
        second_body = second.json()
        assert len(second_body["items"]) == 2
        assert second_body["next_cursor"] is not None

        third = client.get(
            CLIENTS,
            params={"limit": 2, "cursor": second_body["next_cursor"]},
            headers=headers,
        )
        third_body = third.json()
        assert len(third_body["items"]) == 1
        assert third_body["next_cursor"] is None

        seen = [item["id"] for item in first_body["items"] + second_body["items"]]
        assert len(set(seen)) == 4

        by_name = client.get(CLIENTS, params={"query": "carla dias"}, headers=headers)
        assert [item["name"] for item in by_name.json()["items"]] == ["Carla Dias"]

        archived_id = first_body["items"][0]["id"]
        assert client.post(f"{CLIENTS}/{archived_id}/archive", headers=headers).status_code == 200
        archived = client.get(CLIENTS, params={"status": "archived"}, headers=headers)
        assert [item["id"] for item in archived.json()["items"]] == [archived_id]

    def test_invalid_cursor_is_rejected(self, client: TestClient) -> None:
        token = register_user(client)
        response = client.get(CLIENTS, params={"cursor": "not-a-cursor"}, headers=bearer(token))
        assert response.status_code == 422

    def test_invalid_status_filter_is_rejected(self, client: TestClient) -> None:
        token = register_user(client)
        response = client.get(CLIENTS, params={"status": "unknown"}, headers=bearer(token))
        assert response.status_code == 422


class TestAuthorization:
    def test_advisor_can_manage_clients(self, client: TestClient) -> None:
        register_user(client, "ana@basis.dev")
        advisor_token = register_user(client, "bruno@basis.dev")

        response = client.post(
            CLIENTS,
            json={
                "name": "Cliente do Assessor",
                "email": "cliente@example.com",
                "tax_id": CNPJ,
            },
            headers=bearer(advisor_token),
        )
        assert response.status_code == 201

    def test_authenticated_user_can_list(self, client: TestClient) -> None:
        token = register_user(client)
        assert client.get(CLIENTS, headers=bearer(token)).status_code == 200
