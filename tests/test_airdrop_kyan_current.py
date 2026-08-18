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
        "verified_gated_action_count": 1,
        "safe_auth_required_count": 0,
        "auto_executed_action_count": 0,
        "primary_approval_required_count": 1,
        "additional_approval_required_count": 0,
        "approval_required_count": 1,
        "blocked_unverified_count": 0,
        "reverify_required_count": 0,
        "discovery_only_count": 0,
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "additional_approval_paths": [],
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


def test_fresh_kyan_overlay_promotes_reverify_action_and_refreshes_counts() -> None:
    status, acquisition = _reports()
    action = acquisition["actions"][0]
    action.update(
        {
            "acquisition_state": "REVERIFY_REQUIRED",
            "requires_user_approval": False,
            "requires_funds": False,
            "requires_wallet_signature": False,
            "requires_real_order": False,
            "requires_asset_move": False,
        }
    )
    acquisition["verified_gated_action_count"] = 0
    acquisition["primary_approval_required_count"] = 0
    acquisition["approval_required_count"] = 0
    acquisition["reverify_required_count"] = 1

    updated_status, updated_acquisition, changed = apply_kyan_current(
        status,
        acquisition,
        now=datetime(2026, 8, 20, 3, 30, tzinfo=UTC),
    )

    assert changed is True
    assert updated_status["targets"][0]["program_lifecycle_status"] == "ACTIVE"
    promoted = updated_acquisition["actions"][0]
    assert promoted["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert promoted["requires_user_approval"] is True
    assert promoted["requires_funds"] is True
    assert promoted["requires_wallet_signature"] is True
    assert promoted["requires_real_order"] is True
    assert promoted["action_taken"] == "NONE"
    assert promoted["auto_executed"] is False
    assert updated_acquisition["verified_gated_action_count"] == 1
    assert updated_acquisition["primary_approval_required_count"] == 1
    assert updated_acquisition["approval_required_count"] == 1
    assert updated_acquisition["reverify_required_count"] == 0

    assert updated_acquisition["financial_actions_executed"] == 0
    assert updated_acquisition["asset_transfers_executed"] == 0
    assert updated_acquisition["wallet_signatures_executed"] == 0
    assert updated_acquisition["live_orders_executed"] == 0


def test_kyan_current_demotes_its_previous_output_after_evidence_ttl() -> None:
    status, acquisition = _reports()
    promoted_status, promoted_acquisition, changed = apply_kyan_current(
        status,
        acquisition,
        now=datetime(2026, 8, 18, 3, 30, tzinfo=UTC),
    )
    assert changed is True

    updated_status, updated_acquisition, expired_changed = apply_kyan_current(
        promoted_status,
        promoted_acquisition,
        now=datetime(2026, 8, 26, 3, 30, tzinfo=UTC),
    )

    assert expired_changed is True
    target = updated_status["targets"][0]
    assert target["program_lifecycle_status"] == "REVERIFY"
    assert target["program_lifecycle_verified_at"] is None

    action = updated_acquisition["actions"][0]
    assert action["acquisition_state"] == "REVERIFY_REQUIRED"
    assert action["requires_user_approval"] is False
    assert action["requires_funds"] is False
    assert action["requires_wallet_signature"] is False
    assert action["requires_real_order"] is False
    assert action["evidence_status"] == "EXPIRED_REVERIFY_REQUIRED"
    assert action["action_taken"] == "NONE"
    assert action["auto_executed"] is False
    assert updated_acquisition["verified_gated_action_count"] == 0
    assert updated_acquisition["primary_approval_required_count"] == 0
    assert updated_acquisition["approval_required_count"] == 0
    assert updated_acquisition["reverify_required_count"] == 1

    assert updated_acquisition["financial_actions_executed"] == 0
    assert updated_acquisition["asset_transfers_executed"] == 0
    assert updated_acquisition["wallet_signatures_executed"] == 0
    assert updated_acquisition["live_orders_executed"] == 0
    assert updated_acquisition["live_approved"] is False


def test_kyan_current_does_not_promote_pristine_report_after_evidence_ttl() -> None:
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
