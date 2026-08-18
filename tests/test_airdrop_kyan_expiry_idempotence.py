from datetime import UTC, datetime

from crypto_auto_trade.airdrop_kyan_current import (
    KYAN_VERIFIED_AT,
    apply_kyan_current,
)


def test_stale_kyan_overlay_is_idempotent_after_first_demotion() -> None:
    status = {
        "live_approved": False,
        "targets": [
            {
                "slug": "kyan",
                "program_lifecycle_status": "ACTIVE",
                "program_lifecycle_sources": ["https://blog.kyan.blue/"],
                "program_lifecycle_verified_at": KYAN_VERIFIED_AT,
            }
        ],
    }
    acquisition = {
        "live_approved": False,
        "additional_approval_paths": [],
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "actions": [
            {
                "slug": "kyan",
                "verified_at": KYAN_VERIFIED_AT,
                "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
                "requires_user_approval": True,
                "requires_funds": True,
                "requires_wallet_signature": True,
                "requires_real_order": True,
                "requires_asset_move": False,
                "action_taken": "NONE",
                "auto_executed": False,
            }
        ],
    }

    expired_status, expired_acquisition, first_changed = apply_kyan_current(
        status,
        acquisition,
        now=datetime(2026, 8, 26, 3, 30, tzinfo=UTC),
    )
    assert first_changed is True
    assert expired_status["targets"][0]["program_lifecycle_status"] == "REVERIFY"
    assert (
        expired_acquisition["actions"][0]["evidence_status"]
        == "EXPIRED_REVERIFY_REQUIRED"
    )

    second_status, second_acquisition, second_changed = apply_kyan_current(
        expired_status,
        expired_acquisition,
        now=datetime(2026, 8, 26, 4, 30, tzinfo=UTC),
    )

    assert second_changed is False
    assert second_status == expired_status
    assert second_acquisition == expired_acquisition
    assert second_acquisition["financial_actions_executed"] == 0
    assert second_acquisition["asset_transfers_executed"] == 0
    assert second_acquisition["wallet_signatures_executed"] == 0
    assert second_acquisition["live_orders_executed"] == 0
    assert second_acquisition["live_approved"] is False
