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


def test_airdrop_manual_dry_run_can_skip_network_and_honors_terms_guard() -> None:
    client = TestClient(create_app())
    response = client.post("/api/airdrop/dry-run?probe_network=false")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "DRY_RUN"
    assert payload["live_approved"] is False
    assert payload["terms_automation_blocked_count"] == 2
    assert payload["ethereal_current_block_count"] == 2
    assert all(item["live_approved"] is False for item in payload["targets"])
    assert all(item["program_probe"]["ok"] is None for item in payload["targets"])

    decibel = {
        item["slug"]: item
        for item in payload["targets"]
        if item["slug"] in {"decibel-trading", "decibel-liquidity"}
    }
    assert set(decibel) == {"decibel-trading", "decibel-liquidity"}
    assert all(item["status"] == "UNVERIFIED" for item in decibel.values())
    assert all(
        item["terms_automation_status"] == "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED"
        for item in decibel.values()
    )

    ethereal = {
        item["slug"]: item
        for item in payload["targets"]
        if item["slug"] in {"ethereal-trading", "ethereal-margin"}
    }
    assert set(ethereal) == {"ethereal-trading", "ethereal-margin"}
    assert all(item["status"] == "UNVERIFIED" for item in ethereal.values())
    assert all(item["reward_acquisition_state"] == "BLOCKED_UNVERIFIED" for item in ethereal.values())
    assert all("FAIL_CLOSED" in item["current_evidence_status"] for item in ethereal.values())


def test_airdrop_ui_labels_reachability_and_lifecycle_separately() -> None:
    client = TestClient(create_app())
    response = client.get("/static/airdrop.js")
    assert response.status_code == 200
    assert "Program probe" in response.text
    assert "API probe" in response.text
    assert "Reward mechanics" in response.text
    assert "Program lifecycle" in response.text
