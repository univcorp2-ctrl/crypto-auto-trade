# 100+ Strategy Library

The bot now contains 5 core families and 100+ generated, testable strategy variants.

## Families

| family | count | idea |
|---|---:|---|
| `regime_guard` | 18 | Mix trend/range/shock filters. |
| `ema_cross` | 24 | Vary fast/slow EMA speed. |
| `donchian_trend` | 24 | Vary breakout lookback and position size. |
| `rsi_reversion` | 24 | Vary RSI entry/exit and position size. |
| `bollinger_breakout` | 24 | Vary window, band multiple, and position size. |

## Selection method

```bash
python -m crypto_auto_trade.cli best-strategy --iterations 300 --trailing-stop-pct 0.05
```

The best candidate is chosen by rolling-window validation. The score combines:

- average return,
- Sharpe-like score,
- drawdown penalty,
- healthy-rate.

This is deliberately repeatable and visible. It is not a guarantee.

## Why parameterized variants instead of 100 handwritten classes?

Handwritten classes would be hard to audit and easy to break. Parameterized variants keep each family understandable while still testing many tactical variations.

## Hard exit rule

Every variant shares the same mandatory trailing stop after entry.
