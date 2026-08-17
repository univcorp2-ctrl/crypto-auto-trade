from datetime import UTC, datetime

from crypto_auto_trade.airdrop_decibel_referral import apply_decibel_referral_path


def _base_report() -> dict[str, object]:
    return {
        "actions": [{"slug": "decibel-trading"}],
        "additional_approval_paths": [],
        "reward_path_count": 27,
        "verified_additional_path_count": 6,
        "additional_approval_required_count": 6,
        "approval_required_count": 24,
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "auto_executed_action_count": 0,
    }


def test_decibel_referral_path_is_financially_gated_and_increments_queue() -> None:
    result = apply_decibel_referral_path(
        _base_report(),
        now=datetime(2026, 8, 17, 6, 40, tzinfo=UTC),
    )

    assert result["reward_path_count"] == 28
    assert result["verified_additional_path_count"] == 7
    assert result["additional_approval_required_count"] == 7
    assert result["approval_required_count"] == 25

    path = next(path for path in result["additional_approval_paths"] if path["slug"] == "decibel-referral-amps")
    assert path["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert path["reward_share_pct_of_invitee_amps"] == 10
    assert path["published_volume_threshold_usd"] == 25000
    assert path["initial_referral_code_count"] == 5
    assert path["requires_real_order"] is True
    assert path["requires_external_communication"] is True
    assert path["auto_executed"] is False
    assert path["action_taken"] == "NONE"
    assert "self_referral" in path["prohibited_methods"]
    assert "spam_or_mass_outreach" in path["prohibited_methods"]
    assert "express consent" in path["missing_approval"]

    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
    assert result["auto_executed_action_count"] == 0


def test_decibel_referral_path_fails_closed_after_ttl() -> None:
    result = apply_decibel_referral_path(
        _base_report(),
        now=datetime(2026, 8, 25, 6, 40, tzinfo=UTC),
    )

    assert result["reward_path_count"] == 27
    assert result["approval_required_count"] == 24
    assert result["additional_approval_paths"] == []


def test_decibel_referral_path_requires_parent_target() -> None:
    report = _base_report()
    report["actions"] = [{"slug": "other"}]
    result = apply_decibel_referral_path(
        report,
        now=datetime(2026, 8, 17, 6, 40, tzinfo=UTC),
    )

    assert result["reward_path_count"] == 27
    assert result["additional_approval_paths"] == []
