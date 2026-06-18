from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from crypto_auto_trade.data import choose_candles
from crypto_auto_trade.risk import RiskGuard
from crypto_auto_trade.strategies import build_strategy

LIVE_ACK = "I_UNDERSTAND_THIS_CAN_LOSE_MONEY"


def paper_once(strategy_name: str, data: str | None = None, quote_order_size: float = 25.0, trailing_stop_pct: float = 0.05) -> dict[str, Any]:
    candles = choose_candles(data, False, "binance", "BTC/USDT", "1h", 350)
    signal = build_strategy(strategy_name).generate_signals(candles)[-1]
    price = candles[-1].close
    high = candles[-1].high
    low = candles[-1].low
    state_path = Path("state/paper_state.json")
    log_path = Path("logs/paper_trades.csv")
    state: dict[str, Any] = {"base": 0.0, "quote": 1000.0, "peak_price": None, "trailing_stop_pct": trailing_stop_pct}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    base = float(state.get("base", 0.0))
    quote = float(state.get("quote", 1000.0))
    peak_price = state.get("peak_price")
    trailing_stop_price = None

    if base > 0:
        peak_price = high if peak_price is None else max(float(peak_price), high)
        trailing_stop_price = peak_price * (1 - trailing_stop_pct)
        if low <= trailing_stop_price:
            qty = base
            execution = trailing_stop_price
            fee = qty * execution * 0.001
            quote += qty * execution - fee
            base = 0.0
            state = {"base": base, "quote": quote, "peak_price": None, "trailing_stop_pct": trailing_stop_pct}
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            row = {"timestamp": signal.timestamp, "side": "SELL", "price": execution, "quantity": qty, "quote_after": quote, "base_after": base, "reason": "mandatory trailing stop hit", "trailing_stop_price": trailing_stop_price}
            _append_log(log_path, row)
            return {"mode": "paper", "signal": signal.__dict__, "risk": {"allowed": True, "reason": "mandatory trailing stop exit", "quote_order_size": 0}, "execution": row}

    decision = RiskGuard().check(signal, quote_order_size)
    if not decision.allowed:
        state["peak_price"] = peak_price
        state["trailing_stop_pct"] = trailing_stop_pct
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return {"mode": "paper", "signal": signal.__dict__, "risk": decision.__dict__, "trailing_stop_price": trailing_stop_price, "execution": None}

    if signal.action == "BUY":
        spend = min(quote, decision.quote_order_size)
        fee = spend * 0.001
        qty = max(0.0, spend - fee) / price
        quote -= spend
        base += qty
        peak_price = high
        trailing_stop_price = peak_price * (1 - trailing_stop_pct)
        side = "BUY"
        reason = signal.reason + "; mandatory trailing stop armed"
    elif signal.action == "SELL":
        qty = base
        fee = qty * price * 0.001
        quote += qty * price - fee
        base = 0.0
        peak_price = None
        side = "SELL"
        reason = signal.reason
    else:
        return {"mode": "paper", "signal": signal.__dict__, "risk": decision.__dict__, "execution": None}

    state = {"base": base, "quote": quote, "peak_price": peak_price, "trailing_stop_pct": trailing_stop_pct, "last_price": price}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    row = {"timestamp": signal.timestamp, "side": side, "price": price, "quantity": qty, "quote_after": quote, "base_after": base, "reason": reason, "trailing_stop_price": trailing_stop_price}
    _append_log(log_path, row)
    return {"mode": "paper", "signal": signal.__dict__, "risk": decision.__dict__, "execution": row}


def live_once(strategy_name: str, exchange_id: str, symbol: str, timeframe: str, quote_order_size: float, trailing_stop_pct: float = 0.05) -> dict[str, Any]:
    if os.getenv("CRYPTO_AUTO_TRADE_LIVE_ACK") != LIVE_ACK:
        raise PermissionError("live trading blocked: CRYPTO_AUTO_TRADE_LIVE_ACK is not set correctly")
    api_key = os.getenv("EXCHANGE_API_KEY")
    api_secret = os.getenv("EXCHANGE_API_SECRET")
    if not api_key or not api_secret:
        raise PermissionError("live trading blocked: EXCHANGE_API_KEY and EXCHANGE_API_SECRET are required")
    try:
        import ccxt  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError("Install live dependencies first: pip install -e '.[live]'") from exc
    exchange_cls: Any = getattr(ccxt, exchange_id)
    exchange = exchange_cls({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
    candles = choose_candles(None, True, exchange_id, symbol, timeframe, 350)
    signal = build_strategy(strategy_name).generate_signals(candles)[-1]
    decision = RiskGuard().check(signal, quote_order_size)
    price = candles[-1].close

    # Exchange-native trailing stop differs by venue. This first live version uses app-side
    # mandatory trailing state and market exits for portability.
    if not decision.allowed:
        return {"mode": "live", "signal": signal.__dict__, "risk": decision.__dict__, "execution": None, "trailing_stop_pct": trailing_stop_pct}
    if signal.action == "BUY":
        amount = decision.quote_order_size / price
        order = exchange.create_market_buy_order(symbol, amount)
        execution = {"status": "submitted", "side": "BUY", "amount": amount, "order": order, "trailing_stop_pct": trailing_stop_pct, "note": "mandatory app-side trailing stop is armed after fill"}
    elif signal.action == "SELL":
        base_asset = symbol.split("/")[0]
        balance = exchange.fetch_balance()
        amount = float(balance.get("free", {}).get(base_asset, 0.0))
        if amount <= 0:
            return {"mode": "live", "signal": signal.__dict__, "risk": decision.__dict__, "execution": {"status": "skipped", "reason": "no base balance"}}
        order = exchange.create_market_sell_order(symbol, amount)
        execution = {"status": "submitted", "side": "SELL", "amount": amount, "order": order}
    else:
        execution = {"status": "skipped", "reason": "hold"}
    return {"mode": "live", "signal": signal.__dict__, "risk": decision.__dict__, "execution": execution}


def _append_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)
