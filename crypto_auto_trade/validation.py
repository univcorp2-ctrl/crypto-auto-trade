from __future__ import annotations

from crypto_auto_trade.backtest import BacktestConfig, Backtester, forward_test
from crypto_auto_trade.models import Candle
from crypto_auto_trade.strategies import build_strategy, strategy_names


def run_validation_matrix(candles: list[Candle], iterations: int = 200, trailing_stop_pct: float = 0.05) -> dict[str, object]:
    if len(candles) < 120:
        raise ValueError("validation needs at least 120 candles")
    names = strategy_names()
    rows: list[dict[str, object]] = []
    config = BacktestConfig(trailing_stop_pct=trailing_stop_pct)
    for i in range(iterations):
        name = names[i % len(names)]
        window = min(len(candles), 120 + (i * 17) % max(1, len(candles) - 119))
        start = (i * 13) % max(1, len(candles) - window + 1)
        result = Backtester(build_strategy(name), config).run(candles[start : start + window])
        verdict = "healthy" if result.total_return > 0 and result.max_drawdown < 0.25 else "watch"
        if result.max_drawdown >= 0.35:
            verdict = "risk_high"
        rows.append(
            {
                "strategy": name,
                "window": window,
                "start": start,
                "total_return": round(result.total_return, 6),
                "max_drawdown": round(result.max_drawdown, 6),
                "sharpe_like": round(result.sharpe_like, 6),
                "trade_count": len(result.trades),
                "trailing_stop_count": result.as_dict()["trailing_stop_count"],
                "verdict": verdict,
            }
        )
    summary = summarize(rows)
    return {"iterations": iterations, "trailing_stop_pct": trailing_stop_pct, "summary": summary, "best": summary[0] if summary else None, "rows": rows}


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for name in sorted({str(r["strategy"]) for r in rows}):
        selected = [r for r in rows if r["strategy"] == name]
        positives = sum(1 for r in selected if float(r["total_return"]) > 0)
        healthy = sum(1 for r in selected if r["verdict"] == "healthy")
        avg_return = sum(float(r["total_return"]) for r in selected) / len(selected)
        avg_drawdown = sum(float(r["max_drawdown"]) for r in selected) / len(selected)
        avg_sharpe = sum(float(r["sharpe_like"]) for r in selected) / len(selected)
        score = avg_return * 100 + avg_sharpe - avg_drawdown * 50 + healthy / len(selected) * 10
        out.append(
            {
                "strategy": name,
                "runs": len(selected),
                "positive_rate": round(positives / len(selected), 4),
                "healthy_rate": round(healthy / len(selected), 4),
                "avg_return": round(avg_return, 6),
                "avg_drawdown": round(avg_drawdown, 6),
                "avg_sharpe_like": round(avg_sharpe, 6),
                "total_trailing_stops": sum(int(r["trailing_stop_count"]) for r in selected),
                "selection_score": round(score, 6),
            }
        )
    return sorted(out, key=lambda r: float(r["selection_score"]), reverse=True)


def compare_all_strategies(candles: list[Candle], trailing_stop_pct: float = 0.05) -> list[dict[str, object]]:
    config = BacktestConfig(trailing_stop_pct=trailing_stop_pct)
    rows = [Backtester(build_strategy(name), config).run(candles).as_dict() for name in strategy_names()]
    return sorted(rows, key=lambda r: (float(r["total_return"]), -float(r["max_drawdown"])), reverse=True)


def forward_all_strategies(candles: list[Candle], trailing_stop_pct: float = 0.05) -> list[dict[str, object]]:
    config = BacktestConfig(trailing_stop_pct=trailing_stop_pct)
    return [forward_test(build_strategy(name), candles, config) for name in strategy_names()]


def select_best_strategy(candles: list[Candle], iterations: int = 300, trailing_stop_pct: float = 0.05) -> dict[str, object]:
    matrix = run_validation_matrix(candles, iterations=iterations, trailing_stop_pct=trailing_stop_pct)
    best = matrix.get("best")
    return {
        "method": "rolling-window validation across all registered strategy variants",
        "note": "This is not a profit guarantee. It selects the strongest historical candidate under the current sample/data and trailing stop setting.",
        "best": best,
        "strategy_count": len(strategy_names()),
        "iterations": iterations,
        "trailing_stop_pct": trailing_stop_pct,
    }
