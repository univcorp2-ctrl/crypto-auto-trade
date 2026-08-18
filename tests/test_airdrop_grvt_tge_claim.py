from datetime import UTC, datetime

from crypto_auto_trade.airdrop_grvt_tge_claim import apply_grvt_tge_claim_path


def _report() -> dict:
    return {
        "actions": [{"slug": "grvt"}],
        "additional_approval_paths": [],
        "reward_path_count": 29,
        "verified_additional_path_count": 8,
        "additional_approval_required_count": 8,
        "approval_required_count": 26,
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "live_approved": False,
    }


def test_grvt_tge_claim_is_added_only_as_financial_approval_path() -> None:
    result = apply_grvt_tge_claim_path(
        _report(), now=datetime(2026, 8, 18, 1, 23, tzinfo=UTC)
    )

    path = result["additional_approval_paths"][0]
    assert path["slug"] == "grvt-tge-tranche-claim"
    assert path["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert path["requires_user_approval"] is True
    assert path["requires_funds"] is False
    assert path["requires_real_order"] is False
    assert path["requires_wallet_signature"] is False
    assert path["requires_asset_move"] is True
    assert path["action_taken"] == "NONE"
    assert path["auto_executed"] is False
    assert path["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "2026_07_27_VS_2026_08_06" in path["source_conflict"]
    assert "30-day" in path["known_cost_or_risk"]
    assert "explicit approval" in path["next_action"]

    assert result["reward_path_count"] == 30
    assert result["verified_additional_path_count"] == 9
    assert result["additional_approval_required_count"] == 9
    assert result["approval_required_count"] == 27
    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
    assert result["live_approved"] is False


def test_grvt_tge_claim_is_not_added_after_evidence_ttl() -> None:
    result = apply_grvt_tge_claim_path(
        _report(), now=datetime(2026, 8, 26, 1, 23, tzinfo=UTC)
    )

    assert result["additional_approval_paths"] == []
    assert result["reward_path_count"] == 29
    assert result["approval_required_count"] == 26
