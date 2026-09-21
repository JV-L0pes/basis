"""HTTP tests for the authentication surface."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from basis.modules.identity.presentation.router import REFRESH_COOKIE_NAME

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"

PASSWORD = "s3nh4-forte"

VALID_REGISTRATION = {
    "email": "ana@basis.dev",
    "password": PASSWORD,
    "display_name": "Ana Souza",
}


def register(client: TestClient, email: str = "ana@basis.dev") -> dict[str, Any]:
    response = client.post(REGISTER, json={**VALID_REGISTRATION, "email": email})
    assert response.status_code == 201, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestRegister:
    def test_first_user_is_created_as_admin(self, client: TestClient) -> None:
        body = register(client)
        assert body["user"]["role"] == "admin"
        assert body["user"]["email"] == "ana@basis.dev"
        assert body["token"]["token_type"] == "bearer"
        assert body["token"]["expires_in"] > 0

    def test_refresh_cookie_is_http_only(self, client: TestClient) -> None:
        register(client)
        cookie = client.cookies.get(REFRESH_COOKIE_NAME)
        assert cookie is not None

    def test_second_user_is_advisor(self, client: TestClient) -> None:
        register(client)
        body = register(client, "bruno@basis.dev")
        assert body["user"]["role"] == "advisor"

    def test_duplicate_email_conflicts(self, client: TestClient) -> None:
        register(client)
        response = client.post(REGISTER, json=VALID_REGISTRATION)
        assert response.status_code == 409
        problem = response.json()
        assert problem["code"] == "conflict"
        assert problem["type"].endswith("/conflict")
        assert response.headers["content-type"].startswith("application/problem+json")

    def test_weak_password_is_rejected_with_problem_details(self, client: TestClient) -> None:
        response = client.post(REGISTER, json={**VALID_REGISTRATION, "password": "fraca"})
        assert response.status_code == 422
        problem = response.json()
        assert problem["code"] == "validation_error"
        assert problem["errors"][0]["loc"] == ["body", "password"]

    def test_invalid_email_is_rejected(self, client: TestClient) -> None:
        response = client.post(REGISTER, json={**VALID_REGISTRATION, "email": "nao-e-email"})
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"


class TestLogin:
    def test_login_returns_tokens(self, client: TestClient) -> None:
        register(client)
        response = client.post(LOGIN, json={"email": "ana@basis.dev", "password": PASSWORD})
        assert response.status_code == 200
        assert response.json()["token"]["access_token"]

    def test_wrong_password_returns_401_problem(self, client: TestClient) -> None:
        register(client)
        response = client.post(LOGIN, json={"email": "ana@basis.dev", "password": "errada-123"})
        assert response.status_code == 401
        problem = response.json()
        assert problem["code"] == "unauthenticated"
        assert problem["status"] == 401

    def test_login_is_case_insensitive_on_email(self, client: TestClient) -> None:
        register(client)
        response = client.post(LOGIN, json={"email": "ANA@BASIS.DEV", "password": PASSWORD})
        assert response.status_code == 200


class TestProfile:
    def test_me_requires_authentication(self, client: TestClient) -> None:
        response = client.get(ME)
        assert response.status_code == 401
        assert response.json()["code"] == "unauthenticated"

    def test_me_returns_current_user(self, client: TestClient) -> None:
        access = register(client)["token"]["access_token"]
        response = client.get(ME, headers=bearer(str(access)))
        assert response.status_code == 200
        assert response.json()["email"] == "ana@basis.dev"

    def test_me_rejects_garbage_token(self, client: TestClient) -> None:
        response = client.get(ME, headers=bearer("not-a-jwt"))
        assert response.status_code == 401


class TestRefreshRotation:
    def test_refresh_rotates_the_cookie(self, client: TestClient) -> None:
        register(client)
        first_cookie = client.cookies[REFRESH_COOKIE_NAME]

        response = client.post(REFRESH)
        assert response.status_code == 200
        assert client.cookies[REFRESH_COOKIE_NAME] != first_cookie
        assert response.json()["token"]["access_token"]

    def test_reusing_a_rotated_cookie_is_rejected_and_kills_sessions(
        self, client: TestClient
    ) -> None:
        register(client)
        first_cookie = client.cookies[REFRESH_COOKIE_NAME]

        assert client.post(REFRESH).status_code == 200
        second_cookie = client.cookies[REFRESH_COOKIE_NAME]

        client.cookies.set(REFRESH_COOKIE_NAME, first_cookie)
        response = client.post(REFRESH)
        assert response.status_code == 401
        assert "already been used" in response.json()["detail"]

        client.cookies.set(REFRESH_COOKIE_NAME, second_cookie)
        assert client.post(REFRESH).status_code == 401

    def test_refresh_without_cookie_is_rejected(self, client: TestClient) -> None:
        response = client.post(REFRESH)
        assert response.status_code == 401
        assert response.json()["code"] == "unauthenticated"


class TestLogout:
    def test_logout_clears_the_session(self, client: TestClient) -> None:
        register(client)
        assert client.post(LOGOUT).status_code == 204
        assert client.cookies.get(REFRESH_COOKIE_NAME) is None
        assert client.post(REFRESH).status_code == 401


class TestChangePassword:
    def test_change_password_invalidates_sessions(self, client: TestClient) -> None:
        access = register(client)["token"]["access_token"]
        response = client.post(
            f"{ME}/change-password",
            headers=bearer(str(access)),
            json={"current_password": PASSWORD, "new_password": "nova-s3nh4-2026"},
        )
        assert response.status_code == 204

        assert client.post(REFRESH).status_code == 401
        assert (
            client.post(
                LOGIN, json={"email": "ana@basis.dev", "password": "nova-s3nh4-2026"}
            ).status_code
            == 200
        )

    def test_wrong_current_password_is_rejected(self, client: TestClient) -> None:
        access = register(client)["token"]["access_token"]
        response = client.post(
            f"{ME}/change-password",
            headers=bearer(str(access)),
            json={"current_password": "errada-123", "new_password": "nova-s3nh4-2026"},
        )
        assert response.status_code == 401


class TestRequestContext:
    def test_request_id_is_echoed(self, client: TestClient) -> None:
        response = client.get("/api/v1/health", headers={"X-Request-ID": "test-correlation"})
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "test-correlation"

    def test_generated_request_id_is_present(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.headers.get("X-Request-ID")


class TestHealth:
    def test_liveness(self, client: TestClient) -> None:
        body = client.get("/api/v1/health").json()
        assert body["status"] == "ok"
        assert body["environment"] == "test"

    def test_readiness_checks_database(self, client: TestClient) -> None:
        body = client.get("/api/v1/readyz").json()
        assert body["database"] == "ok"
