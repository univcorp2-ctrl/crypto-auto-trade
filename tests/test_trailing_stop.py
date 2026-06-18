from crypto_auto_trade.backtest import BacktestConfig, Backtester
from crypto_auto_trade.models import Candle, Signal


class AlwaysLongStrategy:
    name = "always_long"

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        return [Signal(c.timestamp, "BUY" if i == 0 else "HOLD", 1.0, "test", "always long") for i, c in enumerate(candles)]


def make_trailing_stop_candles() -> list[Candle]:
    candles: list[Candle] = []
    price = 100.0
    for i in range(95):
        price += 0.2
        candles.append(Candle(str(i), price, price + 1, price - 1, price, 1000))
    candles.append(Candle("peak", 120, 122, 119, 121, 1000))
    candles.append(Candle("drop", 121, 121, 112, 113, 1000))
    return candles


def test_trailing_stop_is_mandatory_after_entry() -> None:
    result = Backtester(AlwaysLongStrategy(), BacktestConfig(trailing_stop_pct=0.05)).run(make_trailing_stop_candles())
    assert result.as_dict()["trailing_stop_count"] >= 1
    assert any("mandatory trailing stop hit" in trade.reason for trade in result.trades)
