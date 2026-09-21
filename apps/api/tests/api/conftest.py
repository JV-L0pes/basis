"""Fixtures for HTTP-level tests (TestClient + per-test database cleanup)."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from basis.config import Settings
from basis.main import create_app
from tests.conftest import truncate_all


@pytest.fixture(autouse=True)
def clean_database(db_url: str, schema: None) -> None:
    truncate_all(db_url)


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    return create_app(test_settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
