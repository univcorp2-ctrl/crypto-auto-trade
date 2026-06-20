from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crypto_auto_trade.backtest import BacktestConfig, Backtester, forward_test
from crypto_auto_trade.data import generate_sample_candles
from crypto_auto_trade.market_data import CoinGeckoClient, generate_synthetic_future_candles
from crypto_auto_trade.strategies import build_strategy, strategy_names
from crypto_auto_trade.validation import select_best_strategy

DEFAULT_COIN_IDS = ["bitcoin", "ethereum", "solana", "ripple", "binancecoin"]
DEFAULT_SCENARIOS = ["bear", "base", "bull", "shock"]


@dataclass(frozen=True)
class SimulationConfig:
    coin_ids: list[str] = field(default_factory=lambda: DEFAULT_COIN_IDS.copy())
    vs_currency: str = "usd"
    years_back: int = 5
    years_forward: int = 5
    trailing_stop_pct: float = 0.05
    strategy_limit: int = 20
    use_live_history: bool = False
    output_dir: str = "data/simulation_results"


def run_five_year_simulation(config: SimulationConfig | None = None) -> dict[str, Any]:
    cfg = config or SimulationConfig()
    client = CoinGeckoClient()
    strategies = strategy_names()[: max(1, cfg.strategy_limit)]
    result: dict[str, Any] = {
        "created_at": datetime.now(tz=UTC).isoformat(),
        "note": "Past 5Y uses historical candles when use_live_history is true; future 5Y is scenario simulation, not known future prices.",
        "config": cfg.__dict__,
        "coins": [],
    }

    for coin_id in cfg.coin_ids:
        candles = _load_history(client, coin_id, cfg)
        coin_payload: dict[str, Any] = {
            "coin_id": coin_id,
            "history_candles": len(candles),
            "past_5y": [],
            "forward_split": [],
            "future_5y_scenarios": [],
            "best_candidate": select_best_strategy(candles, iterations=min(300, max(30, len(strategies) * 4)), trailing_stop_pct=cfg.trailing_stop_pct),
        }
        backtest_config = BacktestConfig(trailing_stop_pct=cfg.trailing_stop_pct)
        for name in strategies:
            try:
                strategy = build_strategy(name)
                past = Backtester(strategy, backtest_config).run(candles).as_dict()
                coin_payload["past_5y"].append(_compact_result(past))
                coin_payload["forward_split"].append(_compact_forward(forward_test(strategy, candles, backtest_config)))
            except Exception as exc:  # defensive simulation logging
                coin_payload["past_5y"].append({"strategy": name, "error": str(exc)})
        best_name = _best_strategy_name(coin_payload["past_5y"]) or "regime_guard"
        for scenario in DEFAULT_SCENARIOS:
            future = generate_synthetic_future_candles(candles, years=cfg.years_forward, scenario=scenario)
            try:
                future_result = Backtester(build_strategy(best_name), backtest_config).run(future).as_dict()
                coin_payload["future_5y_scenarios"].append({"scenario": scenario, "strategy": best_name, **_compact_result(future_result)})
            except Exception as exc:
                coin_payload["future_5y_scenarios"].append({"scenario": scenario, "strategy": best_name, "error": str(exc)})
        result["coins"].append(coin_payload)

    output = save_simulation_result(result, cfg.output_dir)
    result["output_path"] = str(output)
    return result


def list_simulation_results(output_dir: str | Path = "data/simulation_results") -> list[dict[str, Any]]:
    path = Path(output_dir)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for file in sorted(path.glob("simulation_*.json"), reverse=True):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            rows.append({"path": str(file), "created_at": data.get("created_at"), "coins": len(data.get("coins", [])), "note": data.get("note")})
        except json.JSONDecodeError:
            continue
    return rows


def save_simulation_result(payload: dict[str, Any], output_dir: str | Path = "data/simulation_results") -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    filename = datetime.now(tz=UTC).strftime("simulation_%Y%m%dT%H%M%SZ.json")
    output = path / filename
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _load_history(client: CoinGeckoClient, coin_id: str, cfg: SimulationConfig):
    if cfg.use_live_history:
        try:
            return client.five_year_daily_candles(coin_id, cfg.vs_currency)
        except Exception:
            # The app remains usable without a paid API key or network.
            return generate_sample_candles(count=365 * cfg.years_back)
    return generate_sample_candles(count=365 * cfg.years_back)


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy": result.get("strategy"),
        "total_return": result.get("total_return"),
        "max_drawdown": result.get("max_drawdown"),
        "sharpe_like": result.get("sharpe_like"),
        "trade_count": result.get("trade_count"),
        "trailing_stop_count": result.get("trailing_stop_count"),
        "final_equity": result.get("final_equity"),
    }


def _compact_forward(result: dict[str, Any]) -> dict[str, Any]:
    forward = result.get("forward", {}) if isinstance(result, dict) else {}
    train = result.get("train", {}) if isinstance(result, dict) else {}
    return {
        "strategy": result.get("strategy"),
        "verdict": result.get("verdict"),
        "train_return": train.get("total_return"),
        "forward_return": forward.get("total_return"),
        "forward_drawdown": forward.get("max_drawdown"),
    }


def _best_strategy_name(rows: list[dict[str, Any]]) -> str | None:
    valid = [row for row in rows if "error" not in row and row.get("strategy")]
    if not valid:
        return None
    best = sorted(valid, key=lambda row: (float(row.get("total_return") or 0.0), -float(row.get("max_drawdown") or 1.0)), reverse=True)[0]
    return str(best["strategy"])
