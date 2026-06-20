import pytest

from crypto_auto_trade.trader import live_once, paper_once
from crypto_auto_trade.web import create_app


def test_paper_once_runs() -> None:
    result = paper_once("ema_cross", None, 25, 0.05)
    assert result["mode"] == "paper"
    assert "signal" in result


def test_live_requires_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRYPTO_AUTO_TRADE_LIVE_ACK", raising=False)
    with pytest.raises(PermissionError):
        live_once("regime_guard", "binance", "BTC/USDT", "1h", 15, 0.05)


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


def test_web_simulations_endpoint() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.get("/api/simulations")
    assert response.status_code == 200
    assert "results" in response.json()
