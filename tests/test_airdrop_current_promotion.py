from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_current_promotion import promote_current_verified_paths
from crypto_auto_trade.airdrop_live_overrides import OVERRIDE_TTL_DAYS, STANDX_MAKER_VERIFIED_AT


def _report(state: str = "REVERIFY_REQUIRED") -> dict[str, object]:
    return {
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "live_approved": False,
        "primary_approval_required_count": 0,
        "additional_approval_required_count": 0,
        "approval_required_count": 0,
        "blocked_unverified_count": 0,
        "reverify_required_count": 1 if state == "REVERIFY_REQUIRED" else 0,
        "verified_gated_action_count": 0,
        "additional_approval_paths": [],
        "actions": [
            {
                "slug": "standx-maker",
                "acquisition_state": state,
                "requires_user_approval": False,
                "requires_funds": False,
                "requires_wallet_signature": False,
                "requires_real_order": False,
                "requires_asset_move": False,
                "action_taken": "NONE",
                "auto_executed": False,
            }
        ],
    }


def test_fresh_standx_overlay_promotes_reverify_to_financial_approval_only() -> None:
    verified = datetime.fromisoformat(STANDX_MAKER_VERIFIED_AT).astimezone(UTC)
    result = promote_current_verified_paths(_report(), now=verified + timedelta(days=1))
    action = result["actions"][0]

    assert result["current_evidence_promotion_count"] == 1
    assert result["reverify_required_count"] == 0
    assert result["primary_approval_required_count"] == 1
    assert result["approval_required_count"] == 1
    assert result["verified_gated_action_count"] == 1
    assert action["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert action["requires_user_approval"] is True
    assert action["requires_funds"] is True
    assert action["requires_real_order"] is True
    assert action["requires_asset_move"] is False
    assert action["action_taken"] == "NONE"
    assert action["auto_executed"] is False
    assert action["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert action["live_parameters"]["qualifying_band_bps"] == 10
    assert "maximum notional" in action["missing_approval"].lower()
    assert "do not place" in action["next_action"].lower()
    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
    assert result["live_approved"] is False


def test_stale_overlay_does_not_promote_reverify_target() -> None:
    verified = datetime.fromisoformat(STANDX_MAKER_VERIFIED_AT).astimezone(UTC)
    stale = verified + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1)
    result = promote_current_verified_paths(_report(), now=stale)
    action = result["actions"][0]

    assert result["current_evidence_promotion_count"] == 0
    assert result["reverify_required_count"] == 1
    assert result["approval_required_count"] == 0
    assert action["acquisition_state"] == "REVERIFY_REQUIRED"
    assert action["requires_user_approval"] is False
    assert action["action_taken"] == "NONE"
    assert action["auto_executed"] is False


def test_current_approval_state_is_not_double_promoted() -> None:
    verified = datetime.fromisoformat(STANDX_MAKER_VERIFIED_AT).astimezone(UTC)
    result = promote_current_verified_paths(
        _report("APPROVAL_REQUIRED_FINANCIAL"), now=verified + timedelta(days=1)
    )

    assert result["current_evidence_promotion_count"] == 0
    assert result["approval_required_count"] == 1
    assert result["reverify_required_count"] == 0
