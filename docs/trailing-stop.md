# Mandatory Trailing Stop

![Trailing Stop](assets/trailing-stop.svg)

Every strategy must use the same safety rule:

1. BUY creates a position.
2. Bot records the highest high after entry.
3. Bot calculates `trailing_stop_price = peak_price * (1 - trailing_stop_pct)`.
4. If the candle low touches the trailing stop price, the bot exits.

This is implemented in:

- `crypto_auto_trade/backtest.py`
- `crypto_auto_trade/trader.py`
- `crypto_auto_trade/web.py`

The UI exposes `Trailing Stop %` so the user can test 3%, 5%, 10%, etc.
