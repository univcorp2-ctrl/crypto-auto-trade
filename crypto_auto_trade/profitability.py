from __future__ import annotations

from crypto_auto_trade.backtest import BacktestConfig, forward_test
from crypto_auto_trade.models import Candle
from crypto_auto_trade.strategies import build_strategy
from crypto_auto_trade.validation import compare_all_strategies, run_validation_matrix

# Verdict labels. The Japanese label answers the user's question "勝てるか?" directly.
VERDICT_LABELS = {
    "win_likely": "勝てる可能性が高い",
    "marginal": "条件付き・要監視",
    "lose_likely": "現状の設定では勝ちにくい",
}


def verify_profitability(
    candles: list[Candle],
    trailing_stop_pct: float = 0.05,
    iterations: int = 300,
) -> dict[str, object]:
    """Decide whether the strategy library "can win" on the given candles.

    This combines three independent signals:

    - full-sample backtest across every registered strategy variant,
    - rolling-window validation (positive rate / healthy rate / drawdown),
    - an out-of-sample forward test on the strongest candidate.

    It returns an explicit verdict plus the evidence behind it. This is a
    historical, sample-based judgement and never a profit guarantee.
    """
    matrix = run_validation_matrix(candles, iterations=iterations, trailing_stop_pct=trailing_stop_pct)
    summary = matrix["summary"]
    if not summary:
        raise ValueError("validation produced no summary rows")
    best_summary = summary[0]
    best_name = str(best_summary["strategy"])

    backtest_rows = compare_all_strategies(candles, trailing_stop_pct)
    profitable = [row for row in backtest_rows if float(row["total_return"]) > 0]
    profitable_rate = len(profitable) / len(backtest_rows)

    forward = forward_test(build_strategy(best_name), candles, BacktestConfig(trailing_stop_pct=trailing_stop_pct))
    forward_return = float(forward["forward"]["total_return"])
    train_return = float(forward["train"]["total_return"])

    positive_rate = float(best_summary["positive_rate"])
    healthy_rate = float(best_summary["healthy_rate"])
    avg_return = float(best_summary["avg_return"])
    avg_drawdown = float(best_summary["avg_drawdown"])

    checks = {
        "best_avg_return_positive": avg_return > 0,
        "positive_rate_majority": positive_rate >= 0.5,
        "healthy_rate_majority": healthy_rate >= 0.5,
        "forward_return_positive": forward_return > 0,
        "drawdown_acceptable": avg_drawdown < 0.25,
        "library_mostly_profitable": profitable_rate >= 0.5,
    }
    win_score = sum(1 for passed in checks.values() if passed)
    total_checks = len(checks)

    if win_score >= 5 and checks["forward_return_positive"]:
        verdict = "win_likely"
    elif win_score >= 3:
        verdict = "marginal"
    else:
        verdict = "lose_likely"

    return {
        "verdict": verdict,
        "verdict_label": VERDICT_LABELS[verdict],
        "win_score": win_score,
        "max_score": total_checks,
        "confidence": round(win_score / total_checks, 4),
        "best_strategy": best_name,
        "trailing_stop_pct": trailing_stop_pct,
        "iterations": iterations,
        "checks": checks,
        "metrics": {
            "best_avg_return": round(avg_return, 6),
            "best_positive_rate": round(positive_rate, 4),
            "best_healthy_rate": round(healthy_rate, 4),
            "best_avg_drawdown": round(avg_drawdown, 6),
            "library_profitable_rate": round(profitable_rate, 4),
            "library_profitable_count": len(profitable),
            "library_total": len(backtest_rows),
            "forward_train_return": round(train_return, 6),
            "forward_return": round(forward_return, 6),
            "forward_verdict": forward["verdict"],
        },
        "note": (
            "Sample/historical judgement only. A 'win_likely' verdict means the strategy "
            "library was profitable and stable on this data with the current trailing stop; "
            "it is not a guarantee of future profit."
        ),
    }
