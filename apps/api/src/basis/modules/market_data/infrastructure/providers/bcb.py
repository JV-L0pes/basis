"""BCB SGS provider for Brazilian macro series (Selic, CDI, IPCA, USD/BRL)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from basis.kernel.domain.clock import Clock
from basis.modules.market_data.domain.ports import IndexPointView
from basis.modules.market_data.domain.value_objects import MacroSeriesCode
from basis.modules.market_data.infrastructure.providers._http import fetch_json
from basis.modules.market_data.infrastructure.providers._json import (
    as_decimal,
    as_mapping,
    as_sequence,
    parse_bcb_date,
)

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
DEFAULT_TIMEOUT_SECONDS = 10.0


class BcbSgsProvider:
    """Macro series from the Brazilian Central Bank public API."""

    def __init__(self, *, clock: Clock, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._clock = clock
        self._timeout = timeout

    async def get_series(
        self, code: MacroSeriesCode, *, start: date, end: date
    ) -> Sequence[IndexPointView]:
        if end < start:
            return []
        payload = await fetch_json(
            f"{BASE_URL}.{code.bcb_sgs_id}/dados",
            timeout=self._timeout,
            params={
                "formato": "json",
                "dataInicial": start.strftime("%d/%m/%Y"),
                "dataFinal": end.strftime("%d/%m/%Y"),
            },
        )
        points: list[IndexPointView] = []
        for item in as_sequence(payload):
            entry = as_mapping(item)
            value = as_decimal(entry.get("valor"))
            moment = parse_bcb_date(entry.get("data"))
            if value is None or moment is None:
                continue
            points.append(IndexPointView(code=str(code), date=moment, value=value))
        points.sort(key=lambda point: point.date)
        return points

    async def latest(self, code: MacroSeriesCode) -> IndexPointView | None:
        end = self._clock.today()
        start = end - timedelta(days=30)
        series = await self.get_series(code, start=start, end=end)
        return series[-1] if series else None


__all__ = ["BcbSgsProvider"]
