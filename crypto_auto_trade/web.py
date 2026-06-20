from __future__ import annotations

from pathlib import Path
from typing import Any

from crypto_auto_trade.backtest import BacktestConfig, Backtester, forward_test
from crypto_auto_trade.data import choose_candles
from crypto_auto_trade.exchange_registry import api_ready_venues, list_exchange_venues
from crypto_auto_trade.market_data import fetch_and_save_market_snapshot
from crypto_auto_trade.simulation import SimulationConfig, list_simulation_results, run_five_year_simulation
from crypto_auto_trade.strategies import build_strategy, strategy_descriptions, strategy_names
from crypto_auto_trade.trader import paper_once
from crypto_auto_trade.validation import (
    compare_all_strategies,
    forward_all_strategies,
    run_validation_matrix,
    select_best_strategy,
)

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"


def create_app() -> Any:
    try:
        from fastapi import FastAPI, Query
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise ImportError("Install web dependencies first: pip install -e '.[web]'") from exc
    app = FastAPI(title="Crypto Auto Trade", version="0.1.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"ok": True, "service": "crypto-auto-trade", "strategy_count": len(strategy_names()), "exchange_count": len(list_exchange_venues())}

    @app.get("/api/strategies")
    def strategies(include_variants: bool = True) -> dict[str, object]:
        return {"strategies": strategy_descriptions(include_variants=include_variants), "count": len(strategy_names())}

    @app.get("/api/exchanges")
    def exchanges(api_ready_only: bool = False) -> dict[str, object]:
        venues = api_ready_venues() if api_ready_only else list_exchange_venues()
        return {"exchanges": [venue.__dict__ for venue in venues], "count": len(venues)}

    @app.get("/api/market/prices")
    def market_prices(vs_currency: str = "usd", pages: int = 1, per_page: int = 100) -> dict[str, object]:
        return fetch_and_save_market_snapshot(vs_currency=vs_currency, pages=max(1, pages), per_page=min(max(1, per_page), 250))

    @app.post("/api/simulations/five-year")
    def api_five_year_simulation(coin_ids: str = "bitcoin,ethereum,solana,ripple,binancecoin", vs_currency: str = "usd", trailing_stop_pct: float = 0.05, strategy_limit: int = 20, live_history: bool = False) -> dict[str, object]:
        config = SimulationConfig(
            coin_ids=[coin.strip() for coin in coin_ids.split(",") if coin.strip()],
            vs_currency=vs_currency,
            trailing_stop_pct=trailing_stop_pct,
            strategy_limit=min(max(1, strategy_limit), 120),
            use_live_history=live_history,
        )
        return run_five_year_simulation(config)

    @app.get("/api/simulations")
    def simulations() -> dict[str, object]:
        return {"results": list_simulation_results()}

    @app.get("/api/backtest")
    def api_backtest(strategy: str = Query("regime_guard", enum=strategy_names()), data_source: str = "sample", exchange: str = "binance", symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 350, trailing_stop_pct: float = 0.05) -> dict[str, object]:
        candles = choose_candles(None, data_source == "live", exchange, symbol, timeframe, limit)
        return Backtester(build_strategy(strategy), BacktestConfig(trailing_stop_pct=trailing_stop_pct)).run(candles).as_dict()

    @app.get("/api/forward-test")
    def api_forward(strategy: str = Query("regime_guard", enum=strategy_names()), data_source: str = "sample", exchange: str = "binance", symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 350, trailing_stop_pct: float = 0.05) -> dict[str, object]:
        candles = choose_candles(None, data_source == "live", exchange, symbol, timeframe, limit)
        return forward_test(build_strategy(strategy), candles, BacktestConfig(trailing_stop_pct=trailing_stop_pct))

    @app.get("/api/realtime")
    def api_realtime(strategy: str = Query("regime_guard", enum=strategy_names()), exchange: str = "binance", symbol: str = "BTC/USDT", timeframe: str = "1h", live: bool = False, limit: int = 350, trailing_stop_pct: float = 0.05) -> dict[str, object]:
        candles = choose_candles(None, live, exchange, symbol, timeframe, limit)
        result = Backtester(build_strategy(strategy), BacktestConfig(trailing_stop_pct=trailing_stop_pct)).run(candles).as_dict()
        result["source"] = "live" if live else "sample"
        result["symbol"] = symbol
        result["timeframe"] = timeframe
        return result

    @app.get("/api/compare")
    def api_compare(data_source: str = "sample", exchange: str = "binance", symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 350, trailing_stop_pct: float = 0.05) -> dict[str, object]:
        candles = choose_candles(None, data_source == "live", exchange, symbol, timeframe, limit)
        return {"backtest": compare_all_strategies(candles, trailing_stop_pct), "forward": forward_all_strategies(candles, trailing_stop_pct)}

    @app.get("/api/validate")
    def api_validate(iterations: int = 300, data_source: str = "sample", exchange: str = "binance", symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 350, trailing_stop_pct: float = 0.05) -> dict[str, object]:
        candles = choose_candles(None, data_source == "live", exchange, symbol, timeframe, limit)
        return run_validation_matrix(candles, iterations, trailing_stop_pct)

    @app.get("/api/best-strategy")
    def api_best(iterations: int = 300, data_source: str = "sample", exchange: str = "binance", symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 350, trailing_stop_pct: float = 0.05) -> dict[str, object]:
        candles = choose_candles(None, data_source == "live", exchange, symbol, timeframe, limit)
        return select_best_strategy(candles, iterations, trailing_stop_pct)

    @app.post("/api/paper-once")
    def api_paper(strategy: str = Query("regime_guard", enum=strategy_names()), quote_order_size: float = 25.0, trailing_stop_pct: float = 0.05) -> dict[str, object]:
        return paper_once(strategy, None, quote_order_size, trailing_stop_pct)

    return app


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError("Install web dependencies first: pip install -e '.[web]'") from exc
    uvicorn.run("crypto_auto_trade.web:create_app", factory=True, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
