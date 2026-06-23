import pytest

from crypto_auto_trade.trader import live_loop, live_once, paper_loop, paper_once
from crypto_auto_trade.web import create_app


def test_paper_once_runs() -> None:
    result = paper_once("ema_cross", None, 25, 0.05)
    assert result["mode"] == "paper"
    assert "signal" in result


def test_live_requires_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRYPTO_AUTO_TRADE_LIVE_ACK", raising=False)
    with pytest.raises(PermissionError):
        live_once("regime_guard", "binance", "BTC/USDT", "1h", 15, 0.05)


def test_live_requires_keys_even_with_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRYPTO_AUTO_TRADE_LIVE_ACK", "I_UNDERSTAND_THIS_CAN_LOSE_MONEY")
    monkeypatch.delenv("EXCHANGE_API_KEY", raising=False)
    monkeypatch.delenv("EXCHANGE_API_SECRET", raising=False)
    with pytest.raises(PermissionError):
        live_once("regime_guard", "binance", "BTC/USDT", "1h", 15, 0.05, testnet=True)


def test_live_loop_fails_fast_on_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # A loop must not spin forever swallowing a misconfiguration.
    monkeypatch.delenv("CRYPTO_AUTO_TRADE_LIVE_ACK", raising=False)
    with pytest.raises(PermissionError):
        live_loop("regime_guard", "binance", "BTC/USDT", "1h", 15, interval_seconds=0, max_iterations=3)


def test_paper_loop_runs_fixed_iterations() -> None:
    results = paper_loop("ema_cross", interval_seconds=0, max_iterations=3)
    assert len(results) == 3
    assert all(r["mode"] == "paper" for r in results)


def test_web_app_health() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "crypto-auto-trade"
    assert payload["strategy_count"] >= 100
    assert payload["exchange_count"] == 32


def test_web_backtest_accepts_trailing_stop() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.get("/api/backtest?strategy=ema_cross&trailing_stop_pct=0.03")
    assert response.status_code == 200
    assert response.json()["trailing_stop_pct"] == 0.03


def test_web_exchanges_endpoint() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.get("/api/exchanges")
    assert response.status_code == 200
    assert response.json()["count"] == 32


def test_web_best_strategy_endpoint() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.get("/api/best-strategy?iterations=30&trailing_stop_pct=0.05")
    assert response.status_code == 200
    assert response.json()["strategy_count"] >= 100
