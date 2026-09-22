"""Development entrypoint.

On Windows the default event loop is ``ProactorEventLoop``, which psycopg's
async mode does not support. This module starts uvicorn on a selector loop,
which works on every platform. Production runs inside Linux containers and can
use ``uvicorn basis.main:app`` directly.
"""

from __future__ import annotations

import asyncio

import uvicorn

from basis.config import get_settings
from basis.main import app


def main() -> None:
    settings = get_settings()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=settings.port,
        log_level="info",
        reload=False,
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)


if __name__ == "__main__":
    main()
