from crypto_auto_trade.data import generate_sample_candles
from crypto_auto_trade.market_data import generate_synthetic_future_candles, market_chart_to_daily_candles
from crypto_auto_trade.simulation import SimulationConfig, run_five_year_simulation


def test_market_chart_to_daily_candles() -> None:
    payload = {
        "prices": [
            [1704067200000, 100.0],
            [1704070800000, 102.0],
            [1704153600000, 103.0],
            [1704157200000, 101.0],
        ],
        "total_volumes": [[1704067200000, 1000.0], [1704153600000, 2000.0]],
    }
    candles = market_chart_to_daily_candles(payload, "bitcoin")
    assert len(candles) == 2
    assert candles[0].open == 100.0
    assert candles[0].close == 102.0


def test_generate_synthetic_future_candles() -> None:
    candles = generate_sample_candles(365)
    future = generate_synthetic_future_candles(candles, years=1, scenario="base")
    assert len(future) == 365
    assert future[0].close > 0


def test_run_five_year_simulation_sample_mode(tmp_path) -> None:
    result = run_five_year_simulation(
        SimulationConfig(
            coin_ids=["bitcoin"],
            strategy_limit=3,
            use_live_history=False,
            output_dir=str(tmp_path),
        )
    )
    assert result["coins"][0]["coin_id"] == "bitcoin"
    assert len(result["coins"][0]["future_5y_scenarios"]) == 4
    assert "output_path" in result
