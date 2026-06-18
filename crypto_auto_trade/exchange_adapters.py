from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from crypto_auto_trade.exchange_registry import ExchangeVenue, get_exchange_venue


@dataclass(frozen=True)
class ExchangeTicker:
    exchange_id: str
    symbol: str
    raw: dict[str, Any]


class PublicExchangeClient:
    def __init__(self, venue: ExchangeVenue) -> None:
        self.venue = venue

    def fetch_ticker(self, symbol: str | None = None) -> ExchangeTicker:
        resolved_symbol = symbol or self.venue.default_symbol
        if self.venue.ticker_url_template:
            url = self.venue.ticker_url_template.format(symbol=urllib.parse.quote(resolved_symbol, safe="_/-"))
            return ExchangeTicker(self.venue.id, resolved_symbol, _get_json(url))
        if self.venue.ccxt_id:
            return self._fetch_ticker_ccxt(resolved_symbol)
        raise NotImplementedError(f"No public ticker adapter is configured for {self.venue.id}")

    def _fetch_ticker_ccxt(self, symbol: str) -> ExchangeTicker:
        try:
            import ccxt  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError("Install live dependencies first: pip install -e '.[live]'") from exc
        exchange_cls = getattr(ccxt, self.venue.ccxt_id)
        exchange = exchange_cls({"enableRateLimit": True})
        return ExchangeTicker(self.venue.id, symbol, exchange.fetch_ticker(symbol))


class PrivateExchangeClient:
    def __init__(self, venue: ExchangeVenue) -> None:
        self.venue = venue

    def explain_required_secrets(self) -> dict[str, Any]:
        return {
            "exchange_id": self.venue.id,
            "name": self.venue.name,
            "required_secrets": list(self.venue.required_secrets),
            "note": "Private trading is intentionally not called unless the live trading command has explicit ACK and secrets.",
        }


def build_public_client(exchange_id: str) -> PublicExchangeClient:
    return PublicExchangeClient(get_exchange_venue(exchange_id))


def build_private_client(exchange_id: str) -> PrivateExchangeClient:
    return PrivateExchangeClient(get_exchange_venue(exchange_id))


def _get_json(url: str, timeout: float = 10.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "crypto-auto-trade/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if isinstance(data, dict):
        return data
    return {"data": data}
