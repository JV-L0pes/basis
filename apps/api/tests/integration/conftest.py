"""Integration-test fixtures: every test starts from an empty database."""

from __future__ import annotations

import pytest

from tests.conftest import truncate_all


@pytest.fixture(autouse=True)
def clean_database(db_url: str, schema: None) -> None:
    truncate_all(db_url)
