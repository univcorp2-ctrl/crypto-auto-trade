from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_ethereal_current import (
    ETHEREAL_VERIFIED_AT,
    TTL_DAYS,
    apply_ethereal_current,
)


def _report() -> dict[str, object]:
    return {
        "live_approved": False,
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "primary_approval_required_count": 1,
        "additional_approval_required_count": 1,
        "approval_required_count": 2,
        "blocked_unverified_count": 0,
        "reverify_required_count": 1,
        "verified_gated_action_count": 1,
        "additional_approval_paths": [
            {"slug": "other-path", "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL"}
        ],
        "actions": [
            {
                "slug": "ethereal-trading",
                "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
                "requires_user_approval": True,
                "requires_funds": True,
                "requires_wallet_signature": True,
                "requires_real_order": True,
                "requires_asset_move": False,
                "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "action_taken": "NONE",
                "auto_executed": False,
            },
            {
                "slug": "ethereal-margin",
                "acquisition_state": "REVERIFY_REQUIRED",
                "requires_user_approval": False,
                "requires_funds": False,
                "requires_wallet_signature": False,
                "requires_real_order": False,
                "requires_asset_move": False,
                "action_taken": "NONE",
                "auto_executed": False,
            },
        ],
    }


def test_current_ethereal_migration_blocks_trading_and_margin_without_execution() -> None:
    verified = datetime.fromisoformat(ETHEREAL_VERIFIED_AT).astimezone(UTC)
    result = apply_ethereal_current(_report(), now=verified + timedelta(minutes=1))
    actions = {item["slug"]: item for item in result["actions"]}

    assert result["ethereal_current_block_count"] == 2
    assert result["blocked_unverified_count"] == 2
    assert result["reverify_required_count"] == 0
    assert result["primary_approval_required_count"] == 0
    assert result["additional_approval_required_count"] == 1
    assert result["approval_required_count"] == 1
    assert result["verified_gated_action_count"] == 0

    for slug in ("ethereal-trading", "ethereal-margin"):
        action = actions[slug]
        assert action["acquisition_state"] == "BLOCKED_UNVERIFIED"
        assert action["automation_permitted"] is False
        assert action["evidence_status"] == "PRIMARY_CURRENT_LIFECYCLE_CONFLICT_FAIL_CLOSED"
        assert action["program_lifecycle_status"] == "CLOSE_ONLY_MIGRATING_TO_MERIDIAN"
        assert action["requires_user_approval"] is False
        assert action["requires_funds"] is False
        assert action["requires_wallet_signature"] is False
        assert action["requires_real_order"] is False
        assert action["requires_asset_move"] is False
        assert action["action_taken"] == "NONE"
        assert action["auto_executed"] is False
        assert "meridian" in action["next_action"].lower()

    assert "reduce-only" in actions["ethereal-trading"]["next_action"].lower()
    assert "do not deposit" in actions["ethereal-margin"]["next_action"].lower()
    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
    assert result["live_approved"] is False


def test_stale_ethereal_overlay_does_not_change_pristine_report() -> None:
    verified = datetime.fromisoformat(ETHEREAL_VERIFIED_AT).astimezone(UTC)
    report = _report()
    stale = verified + timedelta(days=TTL_DAYS, seconds=1)

    result = apply_ethereal_current(report, now=stale)

    assert result["ethereal_current_block_count"] == 0
    assert result["actions"] == report["actions"]
    assert result["blocked_unverified_count"] == 0
    assert result["reverify_required_count"] == 1
    assert result["approval_required_count"] == 2
    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
