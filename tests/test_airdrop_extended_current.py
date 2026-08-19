from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_extended_current import (
    EXTENDED_VERIFIED_AT,
    apply_extended_current_evidence,
    apply_extended_current_status,
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


def _status_report(*targets: dict) -> dict:
    result = {
        "targets": list(targets),
        "ready_dry_run": 0,
        "read_only": 0,
        "unverified": 0,
    }
    for target in targets:
        if target["status"] == "READY_DRY_RUN":
            result["ready_dry_run"] += 1
        elif target["status"] == "READ_ONLY":
            result["read_only"] += 1
        elif target["status"] == "UNVERIFIED":
            result["unverified"] += 1
    return result


def test_fresh_extended_status_propagates_current_primary_evidence() -> None:
    verified = datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
    result = apply_extended_current_status(
        _status_report(
            {
                "slug": "extended-trading",
                "status": "READY_DRY_RUN",
                "api_reward_eligibility": "REVERIFY",
                "program_lifecycle_status": "REVERIFY",
            },
            {
                "slug": "extended-liquidity",
                "status": "READ_ONLY",
                "api_reward_eligibility": "REVERIFY",
                "program_lifecycle_status": "REVERIFY",
            },
        ),
        now=verified + timedelta(minutes=5),
    )
    trading, liquidity = result["targets"]

    assert result["extended_current_status_count"] == 2
    assert result["ready_dry_run"] == 1
    assert result["read_only"] == 1
    assert result["unverified"] == 0
    assert trading["api_reward_eligibility"] == "CONFIRMED"
    assert trading["program_lifecycle_status"] == "ACTIVE"
    assert trading["reward_acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert trading["automation_permitted"] is False
    assert trading["current_evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert liquidity["api_reward_eligibility"] == "CONFIRMED"
    assert liquidity["program_lifecycle_status"] == "ACTIVE"
    assert liquidity["reward_acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert liquidity["automation_permitted"] is False


def test_extended_status_never_relaxes_harder_block() -> None:
    verified = datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
    report = _status_report(
        {
            "slug": "extended-trading",
            "status": "UNVERIFIED",
            "api_reward_eligibility": "UNVERIFIED",
            "program_lifecycle_status": "CONFLICT",
            "reward_acquisition_state": "BLOCKED_UNVERIFIED",
            "blocked_reason": "hard block",
        }
    )
    result = apply_extended_current_status(report, now=verified + timedelta(minutes=5))

    assert result["extended_current_status_count"] == 0
    assert result["targets"][0]["status"] == "UNVERIFIED"
    assert result["targets"][0]["reward_acquisition_state"] == "BLOCKED_UNVERIFIED"
    assert result["targets"][0]["blocked_reason"] == "hard block"


def test_stale_extended_status_does_not_promote() -> None:
    verified = datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
    result = apply_extended_current_status(
        _status_report(
            {
                "slug": "extended-trading",
                "status": "READY_DRY_RUN",
                "api_reward_eligibility": "REVERIFY",
                "program_lifecycle_status": "REVERIFY",
            }
        ),
        now=verified + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1),
    )

    assert result["extended_current_status_count"] == 0
    assert result["targets"][0]["api_reward_eligibility"] == "REVERIFY"
    assert result["targets"][0]["program_lifecycle_status"] == "REVERIFY"


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


def test_current_status_generic_liquidity_approval_is_enriched_not_skipped() -> None:
    verified = datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
    result = apply_extended_current_evidence(
        _report(("extended-liquidity", "APPROVAL_REQUIRED_ASSET_MOVE")),
        now=verified + timedelta(minutes=5),
    )

    assert result["extended_current_promotion_count"] == 1
    action = result["actions"][0]
    assert action["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert action["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert action["requires_user_approval"] is True
    assert action["auto_executed"] is False


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
