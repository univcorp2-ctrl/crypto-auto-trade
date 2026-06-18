# Architecture

![Architecture](assets/architecture-overview.svg)

The app is split into small layers:

1. **Browser UI**: plain HTML/CSS/JS.
2. **FastAPI API**: exposes backtest, forward test, realtime validation, compare, paper trading.
3. **Strategy engine**: five selectable strategies.
4. **Backtester**: applies fees, slippage, equity curve, and mandatory trailing stop.
5. **Risk guard**: blocks oversized or high-risk actions.
6. **Paper/live executor**: runs simulated or guarded live orders.

FastAPI serves static files through `StaticFiles`, so the dashboard remains simple and easy to review.
