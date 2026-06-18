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
from crypto_auto_trade.strategy_variants import VARIANT_SPECS, variant_descriptions


class Strategy(Protocol):
    name: str

    def generate_signals(self, candles: list[Candle]) -> list[Signal]: ...


def _sig(candle: Candle, previous: float, target: float, regime: str, reason: str, risk: float = 0.0) -> Signal:
    action = "BUY" if target > previous else ("SELL" if target < previous else "HOLD")
    return Signal(candle.timestamp, action, round(target, 6), regime, reason, round(risk, 2))


@dataclass(frozen=True)
class RegimeGuardStrategy:
    name: str = "regime_guard"
    fast_ema: int = 20
    slow_ema: int = 80
    atr_window: int = 14
    breakout_lookback: int = 55
    z_window: int = 40
    max_atr_ratio: float = 0.08
    efficiency_threshold: float = 0.25
    mean_entry_z: float = -1.8
    mean_exit_z: float = 0.4
    max_position: float = 1.0
    sideways_position: float = 0.35

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        fast = ema(closes, self.fast_ema)
        slow = ema(closes, self.slow_ema)
        atrs = atr(highs, lows, closes, self.atr_window)
        zs = rolling_zscore(closes, self.z_window)
        target = 0.0
        out: list[Signal] = []
        min_history = max(self.slow_ema + 10, self.breakout_lookback + 1, self.z_window + 1, self.atr_window + 1)
        for i, candle in enumerate(candles):
            previous = target
            if i < min_history or fast[i] is None or slow[i] is None or atrs[i] is None or zs[i] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            atr_ratio = (atrs[i] or 0.0) / candle.close
            risk = min(100.0, atr_ratio / self.max_atr_ratio * 100.0)
            efficiency = range_efficiency(closes, self.breakout_lookback, i) or 0.0
            previous_high = max(highs[i - self.breakout_lookback : i])
            previous_low = min(lows[i - self.breakout_lookback : i])
            shock = atr_ratio > self.max_atr_ratio
            trend_up = candle.close > (slow[i] or 0.0) and (fast[i] or 0.0) > (slow[i] or 0.0) and efficiency >= self.efficiency_threshold
            trend_down = candle.close < (slow[i] or 0.0) and (fast[i] or 0.0) < (slow[i] or 0.0)
            if shock or trend_down:
                target = 0.0
                out.append(_sig(candle, previous, target, "risk_off", "shock/downtrend filter", risk))
            elif trend_up and candle.close > previous_high:
                target = self.max_position
                out.append(_sig(candle, previous, target, "trend_up", "Donchian breakout with EMA trend", risk))
            elif previous > 0 and (candle.close < previous_low or candle.close < (slow[i] or 0.0)):
                target = 0.0
                out.append(_sig(candle, previous, target, "exit", "price broke exit reference", risk))
            elif target == 0 and (zs[i] or 0.0) <= self.mean_entry_z:
                target = self.sideways_position
                out.append(_sig(candle, previous, target, "sideways", "small mean reversion", risk))
            elif target > 0 and (zs[i] or 0.0) >= self.mean_exit_z:
                target = 0.0
                out.append(_sig(candle, previous, target, "sideways_exit", "mean reversion recovered", risk))
            else:
                out.append(_sig(candle, previous, target, "wait", "no confirmed edge", risk))
        return out


@dataclass(frozen=True)
class EmaCrossStrategy:
    name: str = "ema_cross"
    fast_ema: int = 12
    slow_ema: int = 48
    target_position: float = 1.0

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        fast = ema(closes, self.fast_ema)
        slow = ema(closes, self.slow_ema)
        out: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i < self.slow_ema or fast[i] is None or slow[i] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            target = self.target_position if (fast[i] or 0.0) > (slow[i] or 0.0) else 0.0
            out.append(_sig(candle, previous, target, "trend", "fast EMA above/below slow EMA"))
        return out


@dataclass(frozen=True)
class DonchianTrendStrategy:
    name: str = "donchian_trend"
    lookback: int = 55
    target_position: float = 1.0

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        high_band = rolling_high(highs, self.lookback)
        low_band = rolling_low(lows, self.lookback)
        out: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i <= self.lookback or high_band[i - 1] is None or low_band[i - 1] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            if candle.close > (high_band[i - 1] or 0.0):
                target = self.target_position
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
    rsi_window: int = 14
    atr_window: int = 14
    entry_rsi: float = 30.0
    exit_rsi: float = 52.0
    target_position: float = 0.5
    max_atr_ratio: float = 0.08

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        rsis = rsi(closes, self.rsi_window)
        atrs = atr(highs, lows, closes, self.atr_window)
        out: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i < max(self.rsi_window, self.atr_window) or rsis[i] is None or atrs[i] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            risk = min(100.0, ((atrs[i] or 0.0) / candle.close) / self.max_atr_ratio * 100.0)
            if risk > 100:
                target = 0.0
                reason = "volatility shock"
            elif target == 0 and (rsis[i] or 0.0) <= self.entry_rsi:
                target = self.target_position
                reason = "RSI oversold entry"
            elif target > 0 and (rsis[i] or 0.0) >= self.exit_rsi:
                target = 0.0
                reason = "RSI recovery exit"
            else:
                reason = "RSI wait"
            out.append(_sig(candle, previous, target, "rsi", reason, risk))
        return out


@dataclass(frozen=True)
class BollingerBreakoutStrategy:
    name: str = "bollinger_breakout"
    window: int = 20
    multiple: float = 2.0
    trend_ema: int = 80
    target_position: float = 0.75

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        middle, upper, _lower = bollinger_bands(closes, self.window, self.multiple)
        trend = ema(closes, self.trend_ema)
        out: list[Signal] = []
        target = 0.0
        min_history = max(self.window, self.trend_ema)
        for i, candle in enumerate(candles):
            previous = target
            if i < min_history or middle[i] is None or upper[i] is None or trend[i] is None:
                out.append(_sig(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            if target == 0 and candle.close > (upper[i] or 0.0) and candle.close > (trend[i] or 0.0):
                target = self.target_position
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

FAMILY_BUILDERS = {
    "regime_guard": RegimeGuardStrategy,
    "ema_cross": EmaCrossStrategy,
    "donchian_trend": DonchianTrendStrategy,
    "rsi_reversion": RsiReversionStrategy,
    "bollinger_breakout": BollingerBreakoutStrategy,
}


def core_strategy_names() -> list[str]:
    return sorted(BUILDERS)


def strategy_names() -> list[str]:
    return sorted([*BUILDERS.keys(), *VARIANT_SPECS.keys()])


def build_strategy(name: str) -> Strategy:
    if name in BUILDERS:
        return BUILDERS[name]()
    if name in VARIANT_SPECS:
        spec = VARIANT_SPECS[name]
        return FAMILY_BUILDERS[spec.family](name=spec.name, **spec.params)
    raise ValueError(f"unknown strategy: {name}")


def strategy_descriptions(include_variants: bool = True) -> list[dict[str, str]]:
    core = [
        {"name": "regime_guard", "label": "Regime Guard", "family": "regime_guard", "style": "trend + range + shock filter", "best_for": "mixed markets", "risk": "may skip pumps"},
        {"name": "ema_cross", "label": "EMA Cross", "family": "ema_cross", "style": "trend follow", "best_for": "clean trends", "risk": "range whipsaw"},
        {"name": "donchian_trend", "label": "Donchian Trend", "family": "donchian_trend", "style": "breakout", "best_for": "strong breakouts", "risk": "fake breakout"},
        {"name": "rsi_reversion", "label": "RSI Reversion", "family": "rsi_reversion", "style": "mean reversion", "best_for": "ranges", "risk": "downtrend"},
        {"name": "bollinger_breakout", "label": "Bollinger Breakout", "family": "bollinger_breakout", "style": "volatility expansion", "best_for": "expansion", "risk": "fake breakout"},
    ]
    if include_variants:
        core.extend(variant_descriptions())
    return core
