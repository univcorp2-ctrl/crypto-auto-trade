from crypto_auto_trade.data import generate_sample_candles
from crypto_auto_trade.profitability import VERDICT_LABELS, verify_profitability


def test_verify_profitability_shape() -> None:
    candles = generate_sample_candles(360)
    result = verify_profitability(candles, trailing_stop_pct=0.05, iterations=60)
    assert result["verdict"] in VERDICT_LABELS
    assert result["verdict_label"] == VERDICT_LABELS[result["verdict"]]
    assert result["max_score"] == 6
    assert 0 <= result["win_score"] <= result["max_score"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["best_strategy"], str) and result["best_strategy"]
    assert set(result["checks"]).issuperset({"forward_return_positive", "drawdown_acceptable"})
    metrics = result["metrics"]
    assert metrics["library_total"] >= 100
    assert 0 <= metrics["library_profitable_count"] <= metrics["library_total"]


def test_verify_profitability_verdict_thresholds() -> None:
    candles = generate_sample_candles(360)
    result = verify_profitability(candles, trailing_stop_pct=0.05, iterations=60)
    score = result["win_score"]
    if score >= 5 and result["checks"]["forward_return_positive"]:
        assert result["verdict"] == "win_likely"
    elif score >= 3:
        assert result["verdict"] == "marginal"
    else:
        assert result["verdict"] == "lose_likely"


def test_web_verify_profitability_endpoint() -> None:
    from fastapi.testclient import TestClient

    from crypto_auto_trade.web import create_app

    client = TestClient(create_app())
    response = client.get("/api/verify-profitability?iterations=60&trailing_stop_pct=0.05")
    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] in VERDICT_LABELS
    assert payload["max_score"] == 6
