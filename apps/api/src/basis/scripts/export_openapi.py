"""Export the OpenAPI 3.1 contract consumed by the frontend.

Usage::

    uv run python -m basis.scripts.export_openapi          # write the file
    uv run python -m basis.scripts.export_openapi --check  # fail if out of date
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from basis.config import get_settings
from basis.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[5]
CONTRACT_PATH = REPO_ROOT / "packages" / "contracts" / "openapi.json"


def build_contract() -> str:
    app = create_app(get_settings())
    schema = app.openapi()
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the Basis API contract")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with status 1 when the committed contract is out of date",
    )
    arguments = parser.parse_args()

    payload = build_contract()

    if arguments.check:
        if not CONTRACT_PATH.exists():
            print(f"missing contract: {CONTRACT_PATH}", file=sys.stderr)
            return 1
        if CONTRACT_PATH.read_text(encoding="utf-8") != payload:
            print(
                f"contract is out of date: run `pnpm openapi:export` ({CONTRACT_PATH})",
                file=sys.stderr,
            )
            return 1
        print("contract is up to date")
        return 0

    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(payload, encoding="utf-8")
    print(f"contract written to {CONTRACT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CONTRACT_PATH", "build_contract", "main"]
