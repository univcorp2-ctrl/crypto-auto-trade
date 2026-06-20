# Price Data and Simulation Architecture

![Market Data Flow](assets/market-data-flow.svg)

## Data sources

The app uses a layered data design.

1. **Mass market snapshot**: `CoinGeckoClient.top_market_prices` in `crypto_auto_trade/market_data.py`.
2. **Exchange OHLCV**: `fetch_live_ohlcv` in `crypto_auto_trade/data.py` through CCXT.
3. **Five-year daily history**: `CoinGeckoClient.five_year_daily_candles` converts market chart range data into daily candles.
4. **Future scenario candles**: `generate_synthetic_future_candles` creates bear/base/bull/shock scenarios from historical return distribution.

## Output files

Market snapshots:

```text
data/market_snapshots/prices_YYYYMMDDTHHMMSSZ.json
```

Simulation results:

```text
data/simulation_results/simulation_YYYYMMDDTHHMMSSZ.json
```

## CLI

```bash
python -m crypto_auto_trade.cli market-snapshot --vs-currency usd --pages 1 --per-page 250
python -m crypto_auto_trade.cli simulate-five-years --coin-ids bitcoin,ethereum,solana --trailing-stop-pct 0.05 --strategy-limit 20
python -m crypto_auto_trade.cli list-simulation-results
```

## Web endpoints

```text
GET  /api/market/prices
POST /api/simulations/five-year
GET  /api/simulations
```

## Future five-year forward test

Future prices do not exist yet. The app therefore treats future 5Y forward testing as scenario simulation, not a forecast.

Scenarios:

- `bear`
- `base`
- `bull`
- `shock`

Each scenario still uses the same mandatory trailing stop execution layer.
