from fastapi.testclient import TestClient

from crypto_auto_trade.web import create_app


def test_airdrop_dashboard_route() -> None:
    client = TestClient(create_app())
    response = client.get("/airdrop")
    assert response.status_code == 200
    assert "Airdrop Agent" in response.text


def test_airdrop_status_is_safe() -> None:
    client = TestClient(create_app())
    response = client.get("/api/airdrop/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["target_count"] == 20
    assert payload["live_approved"] is False


def test_airdrop_manual_dry_run_can_skip_network() -> None:
    client = TestClient(create_app())
    response = client.post("/api/airdrop/dry-run?probe_network=false")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "DRY_RUN"
    assert payload["live_approved"] is False
    assert all(item["live_approved"] is False for item in payload["targets"])


def test_airdrop_ui_labels_reachability_and_lifecycle_separately() -> None:
    client = TestClient(create_app())
    response = client.get("/static/airdrop.js")
    assert response.status_code == 200
    assert "Program probe" in response.text
    assert "API probe" in response.text
    assert "Reward mechanics" in response.text
    assert "Program lifecycle" in response.text
