from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_live_overrides import OVERRIDE_TTL_DAYS
from crypto_auto_trade.airdrop_nado_current import (
    NADO_VERIFIED_AT,
    apply_nado_current_evidence,
)


def _report(*slugs: str) -> dict[str, object]:
    actions = [
        {
            "slug": slug,
            "acquisition_state": "REVERIFY_REQUIRED",
            "requires_user_approval": False,
            "requires_funds": False,
            "requires_wallet_signature": False,
            "requires_real_order": False,
            "requires_asset_move": False,
            "action_taken": "NONE",
            "auto_executed": False,
        }
        for slug in slugs
    ]
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
        "reverify_required_count": len(actions),
        "verified_gated_action_count": 0,
        "additional_approval_paths": [],
        "actions": actions,
    }


def test_fresh_nado_evidence_promotes_trading_and_nlp_to_approval_only() -> None:
    verified = datetime.fromisoformat(NADO_VERIFIED_AT).astimezone(UTC)
    result = apply_nado_current_evidence(
        _report("nado-trading", "nado-nlp"),
        now=verified + timedelta(minutes=1),
    )
    actions = {item["slug"]: item for item in result["actions"]}

    assert result["nado_current_promotion_count"] == 2
    assert result["reverify_required_count"] == 0
    assert result["primary_approval_required_count"] == 2
    assert result["approval_required_count"] == 2
    assert result["verified_gated_action_count"] == 2

    trading = actions["nado-trading"]
    assert trading["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert trading["requires_user_approval"] is True
    assert trading["requires_funds"] is True
    assert trading["requires_real_order"] is True
    assert trading["requires_asset_move"] is False
    assert trading["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "maximum notional" in trading["missing_approval"].lower()
    assert "do not place" in trading["next_action"].lower()

    nlp = actions["nado-nlp"]
    assert nlp["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert nlp["requires_user_approval"] is True
    assert nlp["requires_funds"] is True
    assert nlp["requires_real_order"] is False
    assert nlp["requires_asset_move"] is True
    assert nlp["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "four-day" in nlp["evidence_note"].lower()
    assert "allocation amount" in nlp["missing_approval"].lower()
    assert "do not deposit" in nlp["next_action"].lower()

    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
    assert result["live_approved"] is False
    assert all(action["action_taken"] == "NONE" for action in result["actions"])
    assert all(action["auto_executed"] is False for action in result["actions"])


def test_stale_nado_evidence_does_not_promote() -> None:
    verified = datetime.fromisoformat(NADO_VERIFIED_AT).astimezone(UTC)
    stale = verified + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1)
    result = apply_nado_current_evidence(_report("nado-trading"), now=stale)
    action = result["actions"][0]

    assert result["nado_current_promotion_count"] == 0
    assert result["reverify_required_count"] == 1
    assert result["approval_required_count"] == 0
    assert action["acquisition_state"] == "REVERIFY_REQUIRED"
    assert action["action_taken"] == "NONE"
    assert action["auto_executed"] is False


def test_existing_approval_state_is_not_double_promoted() -> None:
    verified = datetime.fromisoformat(NADO_VERIFIED_AT).astimezone(UTC)
    report = _report("nado-trading")
    action = report["actions"][0]
    action["acquisition_state"] = "APPROVAL_REQUIRED_FINANCIAL"
    action["requires_user_approval"] = True
    action["requires_funds"] = True
    action["requires_real_order"] = True
    report["reverify_required_count"] = 0
    report["primary_approval_required_count"] = 1
    report["approval_required_count"] = 1

    result = apply_nado_current_evidence(report, now=verified + timedelta(minutes=1))

    assert result["nado_current_promotion_count"] == 0
    assert result["approval_required_count"] == 1
    assert result["reverify_required_count"] == 0
    assert result["actions"][0]["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
