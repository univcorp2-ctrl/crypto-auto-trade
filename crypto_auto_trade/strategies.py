from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from crypto_auto_trade.indicators import (
    atr,
    bollinger_bands,
    ema,
    range_efficiency,
    rolling_high,
    rolling_low,
    rolling_zscore,
    rsi,
)
from crypto_auto_trade.models import Candle, Signal


class Strategy(Protocol):
    name: str

    def generate_signals(self, candles: list[Candle]) -> list[Signal]: ...


def _sig(candle: Candle, previous: float, target: float, regime: str, reason: str, risk: float = 0.0) -> Signal:
    action = "BUY" if target > previous else ("SELL" if target < previous else "HOLD")
    return Signal(candle.timestamp, action, round(target, 6), regime, reason, round(risk, 2))


@dataclass(frozen=True)
class RegimeGuardStrategy:
    name: str = "regime_guard"

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        fast = ema(closes, 20)
        slow = ema(closes, 80)
        atrs = atr(highs, lows, closes, 14)
        zs = rolling_zscore(closes, 40)
        target = 0.0
        out: list[Signal] = []
        for i, candle in enumerate(candles):
            previous = target
            if i < 91 or fast[i] is None or slow[i] is None or atrs[i] is None or zs[i] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            atr_ratio = (atrs[i] or 0.0) / candle.close
            risk = min(100.0, atr_ratio / 0.08 * 100.0)
            efficiency = range_efficiency(closes, 55, i) or 0.0
            previous_high = max(highs[i - 55 : i])
            previous_low = min(lows[i - 55 : i])
            shock = atr_ratio > 0.08
            trend_up = candle.close > (slow[i] or 0.0) and (fast[i] or 0.0) > (slow[i] or 0.0) and efficiency >= 0.25
            trend_down = candle.close < (slow[i] or 0.0) and (fast[i] or 0.0) < (slow[i] or 0.0)
            if shock or trend_down:
                target = 0.0
                out.append(_sig(candle, previous, target, "risk_off", "shock/downtrend filter", risk))
            elif trend_up and candle.close > previous_high:
                target = 1.0
                out.append(_sig(candle, previous, target, "trend_up", "Donchian breakout with EMA trend", risk))
            elif previous > 0 and (candle.close < previous_low or candle.close < (slow[i] or 0.0)):
                target = 0.0
                out.append(_sig(candle, previous, target, "exit", "price broke exit reference", risk))
            elif target == 0 and (zs[i] or 0.0) <= -1.8:
                target = 0.35
                out.append(_sig(candle, previous, target, "sideways", "small mean reversion", risk))
            elif target > 0 and (zs[i] or 0.0) >= 0.4:
                target = 0.0
                out.append(_sig(candle, previous, target, "sideways_exit", "mean reversion recovered", risk))
            else:
                out.append(_sig(candle, previous, target, "wait", "no confirmed edge", risk))
        return out


@dataclass(frozen=True)
class EmaCrossStrategy:
    name: str = "ema_cross"

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        fast = ema(closes, 12)
        slow = ema(closes, 48)
        out: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i < 48 or fast[i] is None or slow[i] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            target = 1.0 if (fast[i] or 0.0) > (slow[i] or 0.0) else 0.0
            out.append(_sig(candle, previous, target, "trend", "fast EMA above/below slow EMA"))
        return out


@dataclass(frozen=True)
class DonchianTrendStrategy:
    name: str = "donchian_trend"

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        high_band = rolling_high(highs, 55)
        low_band = rolling_low(lows, 55)
        out: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i <= 55 or high_band[i - 1] is None or low_band[i - 1] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            if candle.close > (high_band[i - 1] or 0.0):
                target = 1.0
                reason = "close broke previous channel high"
            elif candle.close < (low_band[i - 1] or 0.0):
                target = 0.0
                reason = "close broke previous channel low"
            else:
                reason = "inside channel"
            out.append(_sig(candle, previous, target, "channel", reason))
        return out


@dataclass(frozen=True)
class RsiReversionStrategy:
    name: str = "rsi_reversion"

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        rsis = rsi(closes, 14)
        atrs = atr(highs, lows, closes, 14)
        out: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i < 14 or rsis[i] is None or atrs[i] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            risk = min(100.0, ((atrs[i] or 0.0) / candle.close) / 0.08 * 100.0)
            if risk > 100:
                target = 0.0
                reason = "volatility shock"
            elif target == 0 and (rsis[i] or 0.0) <= 30:
                target = 0.5
                reason = "RSI oversold entry"
            elif target > 0 and (rsis[i] or 0.0) >= 52:
                target = 0.0
                reason = "RSI recovery exit"
            else:
                reason = "RSI wait"
            out.append(_sig(candle, previous, target, "rsi", reason, risk))
        return out


@dataclass(frozen=True)
class BollingerBreakoutStrategy:
    name: str = "bollinger_breakout"

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        middle, upper, _lower = bollinger_bands(closes, 20, 2.0)
        trend = ema(closes, 80)
        out: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i < 80 or middle[i] is None or upper[i] is None or trend[i] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            if target == 0 and candle.close > (upper[i] or 0.0) and candle.close > (trend[i] or 0.0):
                target = 0.75
                reason = "Bollinger breakout"
            elif target > 0 and candle.close < (middle[i] or 0.0):
                target = 0.0
                reason = "below middle band exit"
            else:
                reason = "breakout wait"
            out.append(_sig(candle, previous, target, "bollinger", reason))
        return out


BUILDERS = {
    "regime_guard": RegimeGuardStrategy,
    "ema_cross": EmaCrossStrategy,
    "donchian_trend": DonchianTrendStrategy,
    "rsi_reversion": RsiReversionStrategy,
    "bollinger_breakout": BollingerBreakoutStrategy,
}


def strategy_names() -> list[str]:
    return sorted(BUILDERS)


def build_strategy(name: str) -> Strategy:
    if name not in BUILDERS:
        raise ValueError(f"unknown strategy: {name}")
    return BUILDERS[name]()


def strategy_descriptions() -> list[dict[str, str]]:
    return [
        {"name": "regime_guard", "label": "Regime Guard", "style": "trend + range + shock filter", "best_for": "mixed markets", "risk": "may skip pumps"},
        {"name": "ema_cross", "label": "EMA Cross", "style": "trend follow", "best_for": "clean trends", "risk": "range whipsaw"},
        {"name": "donchian_trend", "label": "Donchian Trend", "style": "breakout", "best_for": "strong breakouts", "risk": "fake breakout"},
        {"name": "rsi_reversion", "label": "RSI Reversion", "style": "mean reversion", "best_for": "ranges", "risk": "downtrend"},
        {"name": "bollinger_breakout", "label": "Bollinger Breakout", "style": "volatility expansion", "best_for": "expansion", "risk": "fake breakout"},
    ]
