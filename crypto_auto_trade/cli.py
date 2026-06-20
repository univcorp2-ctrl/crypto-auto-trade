from __future__ import annotations

import argparse
import json

from crypto_auto_trade.backtest import BacktestConfig, Backtester, forward_test
from crypto_auto_trade.data import choose_candles, load_candles_csv
from crypto_auto_trade.exchange_adapters import build_private_client, build_public_client
from crypto_auto_trade.exchange_registry import api_ready_venues, list_exchange_venues
from crypto_auto_trade.market_data import fetch_and_save_market_snapshot
from crypto_auto_trade.simulation import SimulationConfig, list_simulation_results, run_five_year_simulation
from crypto_auto_trade.strategies import build_strategy, strategy_descriptions, strategy_names
from crypto_auto_trade.trader import live_once, paper_once
from crypto_auto_trade.validation import (
    compare_all_strategies,
    forward_all_strategies,
    run_validation_matrix,
    select_best_strategy,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crypto Auto Trade")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list-strategies")
    sub.add_parser("list-exchanges")
    sub.add_parser("list-api-ready-exchanges")

    market = sub.add_parser("market-snapshot")
    market.add_argument("--vs-currency", default="usd")
    market.add_argument("--pages", type=int, default=1)
    market.add_argument("--per-page", type=int, default=250)

    sim = sub.add_parser("simulate-five-years")
    sim.add_argument("--coin-ids", default="bitcoin,ethereum,solana,ripple,binancecoin")
    sim.add_argument("--vs-currency", default="usd")
    sim.add_argument("--trailing-stop-pct", type=float, default=0.05)
    sim.add_argument("--strategy-limit", type=int, default=20)
    sim.add_argument("--live-history", action="store_true")
    sim.add_argument("--output-dir", default="data/simulation_results")
    sub.add_parser("list-simulation-results")

    ticker = sub.add_parser("exchange-ticker")
    ticker.add_argument("--exchange", default="bitflyer")
    ticker.add_argument("--symbol")
    secrets = sub.add_parser("exchange-secrets")
    secrets.add_argument("--exchange", default="bitflyer")
    backtest = sub.add_parser("backtest")
    backtest.add_argument("--strategy", choices=strategy_names(), default="regime_guard")
    backtest.add_argument("--data")
    backtest.add_argument("--trailing-stop-pct", type=float, default=0.05)
    forward = sub.add_parser("forward-test")
    forward.add_argument("--strategy", choices=strategy_names(), default="regime_guard")
    forward.add_argument("--data")
    forward.add_argument("--trailing-stop-pct", type=float, default=0.05)
    validate = sub.add_parser("validate")
    validate.add_argument("--iterations", type=int, default=200)
    validate.add_argument("--data")
    validate.add_argument("--trailing-stop-pct", type=float, default=0.05)
    best = sub.add_parser("best-strategy")
    best.add_argument("--iterations", type=int, default=300)
    best.add_argument("--data")
    best.add_argument("--trailing-stop-pct", type=float, default=0.05)
    realtime = sub.add_parser("realtime")
    realtime.add_argument("--strategy", choices=strategy_names(), default="regime_guard")
    realtime.add_argument("--exchange", default="binance")
    realtime.add_argument("--symbol", default="BTC/USDT")
    realtime.add_argument("--timeframe", default="1h")
    realtime.add_argument("--limit", type=int, default=350)
    realtime.add_argument("--live-data", action="store_true")
    realtime.add_argument("--trailing-stop-pct", type=float, default=0.05)
    paper = sub.add_parser("paper-once")
    paper.add_argument("--strategy", choices=strategy_names(), default="regime_guard")
    paper.add_argument("--data")
    paper.add_argument("--quote-order-size", type=float, default=25.0)
    paper.add_argument("--trailing-stop-pct", type=float, default=0.05)
    live = sub.add_parser("live-once")
    live.add_argument("--strategy", choices=strategy_names(), default="regime_guard")
    live.add_argument("--exchange", default="binance")
    live.add_argument("--symbol", default="BTC/USDT")
    live.add_argument("--timeframe", default="1h")
    live.add_argument("--quote-order-size", type=float, default=15.0)
    live.add_argument("--trailing-stop-pct", type=float, default=0.05)
    compare = sub.add_parser("compare")
    compare.add_argument("--trailing-stop-pct", type=float, default=0.05)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "list-strategies":
        print(json.dumps(strategy_descriptions(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "list-exchanges":
        print(json.dumps([venue.__dict__ for venue in list_exchange_venues()], indent=2, ensure_ascii=False))
        return 0
    if args.command == "list-api-ready-exchanges":
        print(json.dumps([venue.__dict__ for venue in api_ready_venues()], indent=2, ensure_ascii=False))
        return 0
    if args.command == "market-snapshot":
        print(json.dumps(fetch_and_save_market_snapshot(args.vs_currency, args.pages, args.per_page), indent=2, ensure_ascii=False))
        return 0
    if args.command == "simulate-five-years":
        config = SimulationConfig(
            coin_ids=[coin.strip() for coin in args.coin_ids.split(",") if coin.strip()],
            vs_currency=args.vs_currency,
            trailing_stop_pct=args.trailing_stop_pct,
            strategy_limit=args.strategy_limit,
            use_live_history=args.live_history,
            output_dir=args.output_dir,
        )
        print(json.dumps(run_five_year_simulation(config), indent=2, ensure_ascii=False))
        return 0
    if args.command == "list-simulation-results":
        print(json.dumps(list_simulation_results(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "exchange-ticker":
        ticker = build_public_client(args.exchange).fetch_ticker(args.symbol)
        print(json.dumps(ticker.__dict__, indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "exchange-secrets":
        print(json.dumps(build_private_client(args.exchange).explain_required_secrets(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "backtest":
        result = Backtester(build_strategy(args.strategy), BacktestConfig(trailing_stop_pct=args.trailing_stop_pct)).run(load_candles_csv(args.data))
        print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "forward-test":
        config = BacktestConfig(trailing_stop_pct=args.trailing_stop_pct)
        print(json.dumps(forward_test(build_strategy(args.strategy), load_candles_csv(args.data), config), indent=2, ensure_ascii=False))
        return 0
    if args.command == "validate":
        print(json.dumps(run_validation_matrix(load_candles_csv(args.data), args.iterations, args.trailing_stop_pct), indent=2, ensure_ascii=False))
        return 0
    if args.command == "best-strategy":
        print(json.dumps(select_best_strategy(load_candles_csv(args.data), args.iterations, args.trailing_stop_pct), indent=2, ensure_ascii=False))
        return 0
    if args.command == "realtime":
        candles = choose_candles(None, args.live_data, args.exchange, args.symbol, args.timeframe, args.limit)
        result = Backtester(build_strategy(args.strategy), BacktestConfig(trailing_stop_pct=args.trailing_stop_pct)).run(candles)
        print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "paper-once":
        print(json.dumps(paper_once(args.strategy, args.data, args.quote_order_size, args.trailing_stop_pct), indent=2, ensure_ascii=False))
        return 0
    if args.command == "live-once":
        print(json.dumps(live_once(args.strategy, args.exchange, args.symbol, args.timeframe, args.quote_order_size, args.trailing_stop_pct), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "compare":
        candles = load_candles_csv(None)
        print(json.dumps({"backtest": compare_all_strategies(candles, args.trailing_stop_pct), "forward": forward_all_strategies(candles, args.trailing_stop_pct)}, indent=2, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
