from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_reya_trading_current import (
    REYA_TRADING_VERIFIED_AT,
    TTL_DAYS,
    apply_reya_trading_current,
)


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
                "slug": "reya-trading",
                "acquisition_state": state,
                "requires_user_approval": state.startswith("APPROVAL_REQUIRED"),
                "requires_funds": False,
                "requires_wallet_signature": False,
                "requires_real_order": False,
                "requires_asset_move": False,
                "action_taken": "NONE",
                "auto_executed": False,
            }
        ],
    }


def test_fresh_reya_trading_evidence_promotes_only_to_financial_approval() -> None:
    verified = datetime.fromisoformat(REYA_TRADING_VERIFIED_AT).astimezone(UTC)
    result = apply_reya_trading_current(
        _report(), now=verified + timedelta(minutes=5)
    )
    action = result["actions"][0]

    assert result["reya_trading_current_promotion_count"] == 1
    assert result["reverify_required_count"] == 0
    assert result["approval_required_count"] == 1
    assert action["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert action["requires_user_approval"] is True
    assert action["requires_funds"] is True
    assert action["requires_wallet_signature"] is True
    assert action["requires_real_order"] is True
    assert action["requires_asset_move"] is False
    assert action["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "trade any supported market" in action["evidence_note"].lower()
    assert "maximum notional" in action["missing_approval"].lower()
    assert "do not deposit" in action["next_action"].lower()
    assert action["action_taken"] == "NONE"
    assert action["auto_executed"] is False
    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
    assert result["live_approved"] is False


def test_current_overlay_does_not_override_blocked_target() -> None:
    verified = datetime.fromisoformat(REYA_TRADING_VERIFIED_AT).astimezone(UTC)
    result = apply_reya_trading_current(
        _report("BLOCKED_UNVERIFIED"), now=verified + timedelta(minutes=5)
    )

    assert result["reya_trading_current_promotion_count"] == 0
    assert result["actions"][0]["acquisition_state"] == "BLOCKED_UNVERIFIED"
    assert result["approval_required_count"] == 0
    assert result["blocked_unverified_count"] == 1


def test_owned_overlay_expires_back_to_reverify() -> None:
    verified = datetime.fromisoformat(REYA_TRADING_VERIFIED_AT).astimezone(UTC)
    fresh = apply_reya_trading_current(
        _report(), now=verified + timedelta(minutes=5)
    )
    stale = apply_reya_trading_current(
        fresh, now=verified + timedelta(days=TTL_DAYS, seconds=1)
    )
    action = stale["actions"][0]

    assert stale["reya_trading_current_promotion_count"] == 0
    assert action["acquisition_state"] == "REVERIFY_REQUIRED"
    assert action["requires_user_approval"] is False
    assert action["requires_funds"] is False
    assert action["requires_wallet_signature"] is False
    assert action["requires_real_order"] is False
    assert action["evidence_status"] == "EXPIRED_REVERIFY_REQUIRED"
    assert stale["approval_required_count"] == 0
    assert stale["reverify_required_count"] == 1
