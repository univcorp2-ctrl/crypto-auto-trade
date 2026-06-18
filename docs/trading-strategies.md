# Trading Strategies

![Strategy overview](assets/strategy-overview.svg)

All strategies share one hard rule: **after entry, a trailing stop must be active**.

## Regime Guard

![Regime Guard](assets/regime-guard-detail.svg)

Default strategy. It separates market state:

- trend up,
- trend down,
- sideways,
- shock volatility.

It only trades when the market state fits the setup.

## EMA Cross

Trend-following strategy. Simple and readable.

- BUY: fast EMA above slow EMA.
- EXIT: fast EMA below slow EMA or trailing stop hit.

## Donchian Trend

Breakout strategy.

- BUY: close breaks previous channel high.
- EXIT: channel breakdown or trailing stop hit.

## RSI Reversion

Mean-reversion strategy.

- BUY: RSI oversold.
- EXIT: RSI recovery, volatility shock, or trailing stop hit.

## Bollinger Breakout

Volatility expansion strategy.

- BUY: price breaks upper band with trend filter.
- EXIT: below middle band or trailing stop hit.
