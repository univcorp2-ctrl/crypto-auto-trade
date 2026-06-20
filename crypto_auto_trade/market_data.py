from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.models import Candle

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


@dataclass(frozen=True)
class MarketPrice:
    id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float | None
    total_volume: float | None
    price_change_percentage_24h: float | None
    last_updated: str | None


class CoinGeckoClient:
    """Small REST client for large crypto price snapshots and historical charts.

    It works without a key for public/demo endpoints, but can use COINGECKO_API_KEY
    or COINGECKO_DEMO_API_KEY when the user has one.
    """

    def __init__(self, base_url: str = COINGECKO_BASE_URL, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = os.getenv("COINGECKO_API_KEY") or os.getenv("COINGECKO_DEMO_API_KEY")

    def coins_markets(self, vs_currency: str = "usd", per_page: int = 250, page: int = 1) -> list[MarketPrice]:
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": str(per_page),
            "page": str(page),
            "sparkline": "false",
            "price_change_percentage": "24h",
        }
        data = self._get("/coins/markets", params)
        if not isinstance(data, list):
            raise ValueError("unexpected CoinGecko /coins/markets response")
        return [
            MarketPrice(
                id=str(row.get("id")),
                symbol=str(row.get("symbol", "")).upper(),
                name=str(row.get("name", "")),
                current_price=float(row.get("current_price") or 0.0),
                market_cap=_maybe_float(row.get("market_cap")),
                total_volume=_maybe_float(row.get("total_volume")),
                price_change_percentage_24h=_maybe_float(row.get("price_change_percentage_24h")),
                last_updated=row.get("last_updated"),
            )
            for row in data
        ]

    def top_market_prices(self, vs_currency: str = "usd", pages: int = 1, per_page: int = 250) -> list[MarketPrice]:
        prices: list[MarketPrice] = []
        for page in range(1, pages + 1):
            prices.extend(self.coins_markets(vs_currency=vs_currency, per_page=per_page, page=page))
        return prices

    def market_chart_range(self, coin_id: str, vs_currency: str, start: datetime, end: datetime) -> dict[str, Any]:
        params = {
            "vs_currency": vs_currency,
            "from": str(int(start.timestamp())),
            "to": str(int(end.timestamp())),
        }
        data = self._get(f"/coins/{coin_id}/market_chart/range", params)
        if not isinstance(data, dict):
            raise ValueError("unexpected CoinGecko market chart response")
        return data

    def five_year_daily_candles(self, coin_id: str, vs_currency: str = "usd", end: datetime | None = None) -> list[Candle]:
        resolved_end = end or datetime.now(tz=UTC)
        start = resolved_end - timedelta(days=365 * 5 + 2)
        payload = self.market_chart_range(coin_id, vs_currency, start, resolved_end)
        return market_chart_to_daily_candles(payload, coin_id=coin_id)

    def _get(self, path: str, params: dict[str, str]) -> Any:
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}{path}?{query}"
        headers = {"accept": "application/json", "user-agent": "crypto-auto-trade/0.1"}
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key
            headers["x-cg-pro-api-key"] = self.api_key
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))


def market_chart_to_daily_candles(payload: dict[str, Any], coin_id: str) -> list[Candle]:
    prices = payload.get("prices") or []
    volumes = payload.get("total_volumes") or []
    volume_by_day: dict[str, float] = {}
    for row in volumes:
        if not isinstance(row, list) or len(row) < 2:
            continue
        day = datetime.fromtimestamp(float(row[0]) / 1000, tz=UTC).date().isoformat()
        volume_by_day[day] = volume_by_day.get(day, 0.0) + float(row[1] or 0.0)

    grouped: dict[str, list[float]] = {}
    for row in prices:
        if not isinstance(row, list) or len(row) < 2:
            continue
        day = datetime.fromtimestamp(float(row[0]) / 1000, tz=UTC).date().isoformat()
        price = float(row[1] or 0.0)
        if price > 0:
            grouped.setdefault(day, []).append(price)

    candles: list[Candle] = []
    for day in sorted(grouped):
        values = grouped[day]
        if not values:
            continue
        open_price = values[0]
        close_price = values[-1]
        high = max(values)
        low = min(values)
        if high == low:
            high *= 1.0001
            low *= 0.9999
        candles.append(Candle(f"{day}T00:00:00Z", open_price, high, low, close_price, volume_by_day.get(day, 0.0)))
    if len(candles) < 90:
        raise ValueError(f"not enough historical candles for {coin_id}: {len(candles)}")
    return candles


def save_market_snapshot(prices: list[MarketPrice], output_dir: str | Path = "data/market_snapshots") -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    filename = datetime.now(tz=UTC).strftime("prices_%Y%m%dT%H%M%SZ.json")
    output = path / filename
    output.write_text(json.dumps([price.__dict__ for price in prices], ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def fetch_and_save_market_snapshot(vs_currency: str = "usd", pages: int = 1, per_page: int = 250) -> dict[str, Any]:
    client = CoinGeckoClient()
    prices = client.top_market_prices(vs_currency=vs_currency, pages=pages, per_page=per_page)
    path = save_market_snapshot(prices)
    return {"count": len(prices), "vs_currency": vs_currency, "path": str(path), "prices": [price.__dict__ for price in prices]}


def generate_synthetic_future_candles(seed_candles: list[Candle], years: int = 5, scenario: str = "base") -> list[Candle]:
    if len(seed_candles) < 90:
        raise ValueError("future simulation needs at least 90 seed candles")
    returns = [math.log(seed_candles[i].close / seed_candles[i - 1].close) for i in range(1, len(seed_candles)) if seed_candles[i - 1].close > 0]
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / max(1, len(returns) - 1)
    std = math.sqrt(variance)
    drift_multiplier = {"bear": -0.35, "base": 0.25, "bull": 0.85, "shock": 0.05}.get(scenario, 0.25)
    vol_multiplier = {"bear": 1.25, "base": 1.0, "bull": 1.15, "shock": 2.0}.get(scenario, 1.0)
    days = 365 * years
    price = seed_candles[-1].close
    start = _parse_timestamp(seed_candles[-1].timestamp) + timedelta(days=1)
    candles: list[Candle] = []
    for i in range(days):
        cycle = math.sin(i / 29) * std * 0.35 + math.sin(i / 173) * std * 0.55
        deterministic_noise = math.sin(i * 12.9898 + len(seed_candles) * 78.233) * std * vol_multiplier
        shock = 0.0
        if scenario == "shock" and i % 240 in {0, 1, 2}:
            shock = -std * 6
        daily_return = mean * drift_multiplier + cycle + deterministic_noise * 0.28 + shock
        open_price = price
        close_price = max(0.000001, price * math.exp(daily_return))
        high = max(open_price, close_price) * (1 + abs(daily_return) * 0.55 + 0.002)
        low = min(open_price, close_price) * max(0.000001, 1 - abs(daily_return) * 0.55 - 0.002)
        timestamp = (start + timedelta(days=i)).strftime("%Y-%m-%dT00:00:00Z")
        candles.append(Candle(timestamp, open_price, high, low, close_price, seed_candles[-1].volume))
        price = close_price
    return candles


def _parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(tz=UTC)


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def now_ms() -> int:
    return int(time.time() * 1000)
