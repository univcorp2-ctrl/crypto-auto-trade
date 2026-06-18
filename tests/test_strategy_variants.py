from crypto_auto_trade.strategies import build_strategy, strategy_descriptions, strategy_names
from crypto_auto_trade.strategy_variants import variant_count


def test_strategy_variant_count_is_over_100() -> None:
    assert variant_count() >= 100
    assert len(strategy_names()) >= 105


def test_variant_can_be_built() -> None:
    strategy = build_strategy("ema_cross_f5_s34")
    assert strategy.name == "ema_cross_f5_s34"


def test_strategy_descriptions_include_variants() -> None:
    descriptions = strategy_descriptions()
    assert any(item["name"] == "ema_cross_f5_s34" for item in descriptions)
