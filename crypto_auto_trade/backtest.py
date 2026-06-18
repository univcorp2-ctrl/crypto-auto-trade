from __future__ import annotations

from dataclasses import dataclass

from crypto_auto_trade.indicators import max_drawdown, sharpe_like
from crypto_auto_trade.models import BacktestResult, Candle, Trade
from crypto_auto_trade.strategies import Strategy


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000.0
    fee_rate: float = 0.001
    slippage_bps: float = 5.0
    trailing_stop_pct: float = 0.05

    def __post_init__(self) -> None:
        if not 0.001 <= self.trailing_stop_pct <= 0.5:
            raise ValueError("trailing_stop_pct must be between 0.001 and 0.5")


class Backtester:
    def __init__(self, strategy: Strategy, config: BacktestConfig | None = None) -> None:
        self.strategy = strategy
        self.config = config or BacktestConfig()

    def run(self, candles: list[Candle]) -> BacktestResult:
        if len(candles) < 90:
            raise ValueError("at least 90 candles are recommended")
        signals = self.strategy.generate_signals(candles)
        cash = self.config.initial_cash
        units = 0.0
        avg_entry = 0.0
        peak_price: float | None = None
        round_trips = 0
        wins = 0
        trades: list[Trade] = []
        equity_curve: list[tuple[str, float]] = []
        slip = self.config.slippage_bps / 10_000

        for candle, signal in zip(candles, signals, strict=True):
            price = candle.close

            if units > 0:
                peak_price = candle.high if peak_price is None else max(peak_price, candle.high)
                trailing_stop_price = peak_price * (1 - self.config.trailing_stop_pct)
                if candle.low <= trailing_stop_price:
                    execution = trailing_stop_price * (1 - slip)
                    qty = units
                    notional = qty * execution
                    fee = notional * self.config.fee_rate
                    cash += notional - fee
                    pnl = (execution - avg_entry) * qty - fee
                    round_trips += 1
                    wins += 1 if pnl > 0 else 0
                    units = 0.0
                    avg_entry = 0.0
                    peak_price = None
                    trades.append(
                        Trade(
                            candle.timestamp,
                            "SELL",
                            execution,
                            qty,
                            fee,
                            cash,
                            cash,
                            f"mandatory trailing stop hit ({self.config.trailing_stop_pct:.2%})",
                            trailing_stop_price,
                        )
                    )
                    equity_curve.append((candle.timestamp, cash))
                    continue

            equity = cash + units * price
            target_units = equity * signal.target_position / price
            delta = target_units - units
            if abs(delta) > 1e-10:
                if delta > 0:
                    execution = price * (1 + slip)
                    qty = min(delta, cash / (execution * (1 + self.config.fee_rate)))
                    notional = qty * execution
                    fee = notional * self.config.fee_rate
                    previous_units = units
                    cash -= notional + fee
                    units += qty
                    avg_entry = (avg_entry * previous_units + execution * qty) / units if units else 0.0
                    peak_price = candle.high
                    trailing_stop_price = peak_price * (1 - self.config.trailing_stop_pct)
                    side = "BUY"
                    reason = signal.reason + "; mandatory trailing stop armed"
                else:
                    execution = price * (1 - slip)
                    qty = min(abs(delta), units)
                    notional = qty * execution
                    fee = notional * self.config.fee_rate
                    cash += notional - fee
                    units -= qty
                    trailing_stop_price = peak_price * (1 - self.config.trailing_stop_pct) if peak_price else None
                    side = "SELL"
                    reason = signal.reason
                    if units <= 1e-10:
                        pnl = (execution - avg_entry) * qty - fee
                        round_trips += 1
                        wins += 1 if pnl > 0 else 0
                        units = 0.0
                        avg_entry = 0.0
                        peak_price = None
                trades.append(
                    Trade(
                        candle.timestamp,
                        side,
                        execution,
                        qty,
                        fee,
                        cash,
                        cash + units * price,
                        reason,
                        trailing_stop_price,
                    )
                )
            equity_curve.append((candle.timestamp, cash + units * price))
        final = equity_curve[-1][1]
        return BacktestResult(
            self.strategy.name,
            self.config.initial_cash,
            final,
            final / self.config.initial_cash - 1,
            max_drawdown([e for _, e in equity_curve]),
            sharpe_like(equity_curve),
            wins / round_trips if round_trips else 0.0,
            self.config.trailing_stop_pct,
            trades,
            equity_curve,
            signals,
        )


def forward_test(strategy: Strategy, candles: list[Candle], config: BacktestConfig | None = None, split_ratio: float = 0.7) -> dict[str, object]:
    split = int(len(candles) * split_ratio)
    train = Backtester(strategy, config).run(candles[:split])
    forward = Backtester(strategy, config).run(candles[max(0, split - 90) :])
    verdict = "healthy" if forward.total_return > 0 and forward.max_drawdown < 0.25 else "watch"
    if train.total_return > 0 and forward.total_return < 0:
        verdict = "overfit_or_regime_changed"
    if forward.max_drawdown >= 0.35:
        verdict = "drawdown_too_high"
    return {"strategy": strategy.name, "split_index": split, "train": train.as_dict(), "forward": forward.as_dict(), "verdict": verdict}
