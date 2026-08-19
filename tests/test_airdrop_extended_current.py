from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_extended_current import (
    EXTENDED_VERIFIED_AT,
    apply_extended_current_evidence,
)
from crypto_auto_trade.airdrop_live_overrides import OVERRIDE_TTL_DAYS


def _report(*states: tuple[str, str]) -> dict:
    return {
        "actions": [
            {
                "slug": slug,
                "acquisition_state": state,
                "requires_user_approval": False,
                "requires_funds": False,
                "requires_wallet_signature": False,
                "requires_real_order": False,
                "requires_asset_move": False,
                "action_taken": "NONE",
                "auto_executed": False,
                "points_delta": None,
            }
            for slug, state in states
        ],
        "additional_approval_paths": [],
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
    }


def test_fresh_extended_paths_move_only_to_explicit_approval() -> None:
    verified = datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
    result = apply_extended_current_evidence(
        _report(
            ("extended-trading", "REVERIFY_REQUIRED"),
            ("extended-liquidity", "REVERIFY_REQUIRED"),
        ),
        now=verified + timedelta(minutes=5),
    )
    trading, liquidity = result["actions"]

    assert result["extended_current_promotion_count"] == 2
    assert result["reverify_required_count"] == 0
    assert result["approval_required_count"] == 2

    assert trading["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert trading["requires_user_approval"] is True
    assert trading["requires_funds"] is True
    assert trading["requires_wallet_signature"] is True
    assert trading["requires_real_order"] is True
    assert trading["requires_asset_move"] is False
    assert trading["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "do not place" in trading["next_action"].lower()

    assert liquidity["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert liquidity["requires_user_approval"] is True
    assert liquidity["requires_funds"] is True
    assert liquidity["requires_wallet_signature"] is True
    assert liquidity["requires_real_order"] is False
    assert liquidity["requires_asset_move"] is True
    assert liquidity["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "do not deposit" in liquidity["next_action"].lower()

    assert trading["action_taken"] == "NONE"
    assert liquidity["action_taken"] == "NONE"
    assert trading["auto_executed"] is False
    assert liquidity["auto_executed"] is False
    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0


def test_stale_extended_evidence_does_not_promote() -> None:
    verified = datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
    result = apply_extended_current_evidence(
        _report(("extended-trading", "REVERIFY_REQUIRED")),
        now=verified + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1),
    )

    assert result["extended_current_promotion_count"] == 0
    assert result["actions"][0]["acquisition_state"] == "REVERIFY_REQUIRED"
    assert result["reverify_required_count"] == 1


def test_harder_block_is_never_overridden() -> None:
    verified = datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
    result = apply_extended_current_evidence(
        _report(("extended-trading", "BLOCKED_UNVERIFIED")),
        now=verified + timedelta(minutes=5),
    )

    assert result["extended_current_promotion_count"] == 0
    assert result["actions"][0]["acquisition_state"] == "BLOCKED_UNVERIFIED"
    assert result["blocked_unverified_count"] == 1
    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
