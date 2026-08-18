from datetime import UTC, datetime

from crypto_auto_trade.airdrop_kyan_current import apply_kyan_current


def _reports() -> tuple[dict, dict]:
    status = {
        "live_approved": False,
        "targets": [
            {
                "slug": "kyan",
                "program_lifecycle_status": "REVERIFY",
                "program_lifecycle_sources": [],
            }
        ],
    }
    acquisition = {
        "live_approved": False,
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "actions": [
            {
                "slug": "kyan",
                "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
                "requires_user_approval": True,
                "requires_funds": True,
                "requires_wallet_signature": True,
                "requires_real_order": True,
                "requires_asset_move": False,
                "action_taken": "NONE",
                "auto_executed": False,
                "terms_status": "REVERIFY_CURRENT_KRYSTALS_LIFECYCLE_TERMS_JURISDICTION_ACCOUNT_API_KEY_AND_SIGNING",
            }
        ],
    }
    return status, acquisition


def test_kyan_current_promotes_lifecycle_but_keeps_financial_and_signing_gates() -> None:
    status, acquisition = _reports()
    updated_status, updated_acquisition, changed = apply_kyan_current(
        status,
        acquisition,
        now=datetime(2026, 8, 18, 3, 30, tzinfo=UTC),
    )

    assert changed is True
    target = updated_status["targets"][0]
    assert target["program_lifecycle_status"] == "ACTIVE"

    action = updated_acquisition["actions"][0]
    assert action["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert action["requires_user_approval"] is True
    assert action["requires_funds"] is True
    assert action["requires_wallet_signature"] is True
    assert action["requires_real_order"] is True
    assert action["action_taken"] == "NONE"
    assert action["auto_executed"] is False
    assert action["terms_status"].startswith("KRYSTALS_LIFECYCLE_ACTIVE_REVERIFY_")
    assert "explicit financial/signing approval" in action["next_action"]

    assert updated_acquisition["financial_actions_executed"] == 0
    assert updated_acquisition["asset_transfers_executed"] == 0
    assert updated_acquisition["wallet_signatures_executed"] == 0
    assert updated_acquisition["live_orders_executed"] == 0
    assert updated_acquisition["live_approved"] is False


def test_kyan_current_fails_closed_after_evidence_ttl() -> None:
    status, acquisition = _reports()
    updated_status, updated_acquisition, changed = apply_kyan_current(
        status,
        acquisition,
        now=datetime(2026, 8, 26, 3, 30, tzinfo=UTC),
    )

    assert changed is False
    assert updated_status["targets"][0]["program_lifecycle_status"] == "REVERIFY"
    assert (
        updated_acquisition["actions"][0]["terms_status"]
        == "REVERIFY_CURRENT_KRYSTALS_LIFECYCLE_TERMS_JURISDICTION_ACCOUNT_API_KEY_AND_SIGNING"
    )
