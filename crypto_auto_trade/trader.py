from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Any

from crypto_auto_trade.data import choose_candles
from crypto_auto_trade.risk import RiskGuard
from crypto_auto_trade.strategies import build_strategy

LIVE_ACK = "I_UNDERSTAND_THIS_CAN_LOSE_MONEY"
DUST = 1e-8


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


def _load_live_state(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_live_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def live_once(
    strategy_name: str,
    exchange_id: str,
    symbol: str,
    timeframe: str,
    quote_order_size: float,
    trailing_stop_pct: float = 0.05,
    testnet: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run one live decision against a real (or sandbox) exchange.

    Safety gates, in order:
      1. CRYPTO_AUTO_TRADE_LIVE_ACK must equal LIVE_ACK.
      2. EXCHANGE_API_KEY / EXCHANGE_API_SECRET must be present.
      3. testnet=True flips ccxt into sandbox mode (no real funds).
      4. dry_run=True computes the decision and intended order but sends nothing.

    The mandatory trailing stop is now PERSISTED in state/live_state.json so the
    stop survives across runs of the loop (previous version lost it every call).
    """
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
    if testnet:
        if not getattr(exchange, "has", {}).get("sandbox", True):
            raise RuntimeError(f"{exchange_id} has no sandbox/testnet; pick an exchange with a testnet (e.g. binance, bybit, okx)")
        exchange.set_sandbox_mode(True)

    candles = choose_candles(None, True, exchange_id, symbol, timeframe, 350)
    signal = build_strategy(strategy_name).generate_signals(candles)[-1]
    price = candles[-1].close
    high = candles[-1].high
    low = candles[-1].low
    base_asset = symbol.split("/")[0]
    mode = "testnet" if testnet else ("dry_run" if dry_run else "live")

    state_path = Path("state/live_state.json")
    log_path = Path("logs/live_trades.csv")
    state = _load_live_state(state_path)
    pos = state.get(symbol, {})
    peak_price = pos.get("peak_price")

    # Current base holding: read from the exchange when we can place orders;
    # in dry_run we track an estimate locally so the loop is still observable.
    if dry_run:
        held = float(pos.get("base_estimate", 0.0))
    else:
        balance = exchange.fetch_balance()
        held = float(balance.get("free", {}).get(base_asset, 0.0))

    def persist(new_pos: dict[str, Any]) -> None:
        state[symbol] = new_pos
        _save_live_state(state_path, state)

    base_meta = {"mode": mode, "symbol": symbol, "exchange": exchange_id, "signal": signal.__dict__, "trailing_stop_pct": trailing_stop_pct}

    # 1) Mandatory trailing-stop exit takes priority over any new signal.
    if held > DUST:
        peak_price = high if peak_price is None else max(float(peak_price), high)
        stop_price = peak_price * (1 - trailing_stop_pct)
        if low <= stop_price:
            if dry_run:
                execution = {"status": "would_submit", "side": "SELL", "amount": held, "reason": "trailing stop hit", "trailing_stop_price": stop_price}
                persist({"peak_price": None, "base_estimate": 0.0})
            else:
                order = exchange.create_market_sell_order(symbol, held)
                execution = {"status": "submitted", "side": "SELL", "amount": held, "order": order, "reason": "trailing stop hit", "trailing_stop_price": stop_price}
                persist({"peak_price": None})
            _append_log(log_path, {"timestamp": signal.timestamp, "mode": mode, "side": "SELL", "price": stop_price, "quantity": held, "reason": "mandatory trailing stop hit"})
            return {**base_meta, "risk": {"allowed": True, "reason": "mandatory trailing stop exit"}, "execution": execution}
        # Still holding: keep the (possibly raised) stop armed for next run.
        persist({**pos, "peak_price": peak_price})

    decision = RiskGuard().check(signal, quote_order_size)
    if not decision.allowed:
        return {**base_meta, "risk": decision.__dict__, "execution": None, "trailing_stop_price": (peak_price * (1 - trailing_stop_pct)) if peak_price else None}

    if signal.action == "BUY":
        amount = decision.quote_order_size / price
        if dry_run:
            execution = {"status": "would_submit", "side": "BUY", "amount": amount, "price": price}
            persist({"peak_price": high, "base_estimate": float(pos.get("base_estimate", 0.0)) + amount})
        else:
            order = exchange.create_market_buy_order(symbol, amount)
            execution = {"status": "submitted", "side": "BUY", "amount": amount, "order": order, "note": "mandatory app-side trailing stop armed and persisted"}
            persist({"peak_price": high})
        _append_log(log_path, {"timestamp": signal.timestamp, "mode": mode, "side": "BUY", "price": price, "quantity": amount, "reason": signal.reason})
        return {**base_meta, "risk": decision.__dict__, "execution": execution}

    if signal.action == "SELL":
        if held <= DUST:
            return {**base_meta, "risk": decision.__dict__, "execution": {"status": "skipped", "reason": "no base balance"}}
        if dry_run:
            execution = {"status": "would_submit", "side": "SELL", "amount": held}
            persist({"peak_price": None, "base_estimate": 0.0})
        else:
            order = exchange.create_market_sell_order(symbol, held)
            execution = {"status": "submitted", "side": "SELL", "amount": held, "order": order}
            persist({"peak_price": None})
        _append_log(log_path, {"timestamp": signal.timestamp, "mode": mode, "side": "SELL", "price": price, "quantity": held, "reason": signal.reason})
        return {**base_meta, "risk": decision.__dict__, "execution": execution}

    return {**base_meta, "risk": decision.__dict__, "execution": {"status": "skipped", "reason": "hold"}}


def paper_loop(strategy_name: str, interval_seconds: float, max_iterations: int | None = None, data: str | None = None, quote_order_size: float = 25.0, trailing_stop_pct: float = 0.05) -> list[dict[str, Any]]:
    """Repeatedly run paper_once on an interval. max_iterations=None runs forever."""
    results: list[dict[str, Any]] = []
    i = 0
    while max_iterations is None or i < max_iterations:
        results.append(paper_once(strategy_name, data, quote_order_size, trailing_stop_pct))
        i += 1
        if max_iterations is not None and i >= max_iterations:
            break
        time.sleep(interval_seconds)
    return results


def live_loop(strategy_name: str, exchange_id: str, symbol: str, timeframe: str, quote_order_size: float, interval_seconds: float, max_iterations: int | None = None, trailing_stop_pct: float = 0.05, testnet: bool = False, dry_run: bool = False) -> list[dict[str, Any]]:
    """Repeatedly run live_once on an interval. One transient error does not stop the loop."""
    results: list[dict[str, Any]] = []
    i = 0
    while max_iterations is None or i < max_iterations:
        try:
            results.append(live_once(strategy_name, exchange_id, symbol, timeframe, quote_order_size, trailing_stop_pct, testnet, dry_run))
        except PermissionError:
            raise  # configuration error: fail fast, do not loop
        except Exception as exc:  # noqa: BLE001 - keep the daemon alive on transient API errors
            results.append({"mode": "error", "error": str(exc)})
        i += 1
        if max_iterations is not None and i >= max_iterations:
            break
        time.sleep(interval_seconds)
    return results


def _append_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)
