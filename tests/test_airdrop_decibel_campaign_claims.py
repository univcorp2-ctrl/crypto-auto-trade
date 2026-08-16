from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS, build_acquisition_report
from crypto_auto_trade.airdrop_additional_current_paths import (
    DECIBEL_CAMPAIGN_CLAIM_VERIFIED_AT,
    apply_additional_current_paths,
)
from crypto_auto_trade.airdrop_agents import run_all

VERIFIED = datetime.fromisoformat(DECIBEL_CAMPAIGN_CLAIM_VERIFIED_AT).astimezone(UTC)


def _base_report(*, now: datetime) -> dict[str, object]:
    return build_acquisition_report(run_all(probe_network=False), now=now)


def _path(report: dict[str, object], slug: str) -> dict[str, object]:
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)
    return next(path for path in paths if path["slug"] == slug)


def test_decibel_campaign_claim_is_financial_approval_only() -> None:
    # Apply the older StandX path first so this assertion isolates the newly
    # verified Decibel path and proves count increments are idempotent.
    before = apply_additional_current_paths(
        _base_report(now=VERIFIED - timedelta(seconds=1)),
        now=VERIFIED - timedelta(seconds=1),
    )
    result = apply_additional_current_paths(before, now=VERIFIED + timedelta(seconds=1))
    claim = _path(result, "decibel-campaign-claims")

    assert claim["parent_slug"] == "decibel-trading"
    assert claim["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert claim["requires_user_approval"] is True
    assert claim["requires_funds"] is False
    assert claim["requires_wallet_signature"] is True
    assert claim["requires_real_order"] is False
    assert claim["requires_asset_move"] is True
    assert claim["authentication_recheck_required"] is True
    assert claim["claim_status"] == "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_REWARDS_PAGE_OR_IN_APP_CLAIM"
    assert claim["action_taken"] == "NONE"
    assert claim["auto_executed"] is False
    assert claim["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "USD-denominated stablecoin" in str(claim["evidence_note"])
    assert "/rewards" in str(claim["evidence_note"])
    assert "Claim now" in str(claim["evidence_note"])
    assert "expire" in str(claim["evidence_note"]).lower()
    assert "/rewards" in str(claim["next_action"])
    assert "in-app" in str(claim["next_action"]).lower()
    assert "do not connect/sign a wallet" in str(claim["next_action"]).lower()
    assert "coming soon" not in str(claim["evidence_note"]).lower()

    assert result["reward_path_count"] == before["reward_path_count"] + 1
    assert result["verified_additional_path_count"] == before["verified_additional_path_count"] + 1
    assert result["additional_approval_required_count"] == before["additional_approval_required_count"] + 1
    assert result["approval_required_count"] == before["approval_required_count"] + 1

    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0


def test_decibel_campaign_claim_is_idempotent_and_ttl_gated() -> None:
    current = VERIFIED + timedelta(seconds=1)
    once = apply_additional_current_paths(_base_report(now=current), now=current)
    twice = apply_additional_current_paths(once, now=current)

    paths = twice["additional_approval_paths"]
    assert isinstance(paths, list)
    assert sum(path.get("slug") == "decibel-campaign-claims" for path in paths if isinstance(path, dict)) == 1
    assert twice["reward_path_count"] == once["reward_path_count"]
    assert twice["approval_required_count"] == once["approval_required_count"]

    before = apply_additional_current_paths(
        _base_report(now=VERIFIED - timedelta(seconds=1)),
        now=VERIFIED - timedelta(seconds=1),
    )
    stale = apply_additional_current_paths(
        _base_report(now=VERIFIED + timedelta(days=VERIFICATION_TTL_DAYS, seconds=1)),
        now=VERIFIED + timedelta(days=VERIFICATION_TTL_DAYS, seconds=1),
    )

    for report in (before, stale):
        report_paths = report["additional_approval_paths"]
        assert isinstance(report_paths, list)
        assert all(path.get("slug") != "decibel-campaign-claims" for path in report_paths if isinstance(path, dict))
