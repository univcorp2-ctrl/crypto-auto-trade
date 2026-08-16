from datetime import UTC, datetime

from crypto_auto_trade.airdrop_acquisition import build_acquisition_report
from crypto_auto_trade.airdrop_additional_current_paths import apply_additional_current_paths
from crypto_auto_trade.airdrop_agents import run_all


CURRENT_NOW = datetime(2026, 8, 16, 22, 20, tzinfo=UTC)


def _current_report() -> dict[str, object]:
    base = build_acquisition_report(run_all(probe_network=False), now=CURRENT_NOW)
    return apply_additional_current_paths(base, now=CURRENT_NOW)


def _path(report: dict[str, object], slug: str) -> dict[str, object]:
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)
    return next(path for path in paths if path["slug"] == slug)


def test_lighter_funding_rebate_is_financial_approval_only() -> None:
    report = _current_report()
    path = _path(report, "lighter-funding-rate-rebate")

    assert path["parent_slug"] == "lighter"
    assert path["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert path["requires_user_approval"] is True
    assert path["requires_funds"] is True
    assert path["requires_real_order"] is True
    assert path["requires_asset_move"] is False
    assert path["requires_wallet_signature"] is False
    assert path["auto_executed"] is False
    assert path["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "up to a 15% rebate" in str(path["evidence_note"])
    assert "50,000 LIT" in str(path["evidence_note"])
    assert "daily at 00:00 UTC" in str(path["evidence_note"])
    assert "exceeds $1" in str(path["evidence_note"])
    assert "does not prove positive expected value" in str(path["known_cost_or_risk"])
    assert "separate explicit asset-movement approval" in str(path["missing_approval"])
    assert "do not open a position" in str(path["next_action"]).lower()
    assert path["source_coverage"] == "PRIMARY_OFFICIAL_PLUS_ONE_INDEPENDENT_INDUSTRY_SOURCE_NO_EXPERT_SOURCE"


def test_lighter_funding_rebate_path_never_creates_side_effects() -> None:
    report = _current_report()

    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["auto_executed_action_count"] == 0


def test_lighter_funding_rebate_is_fail_closed_before_verification_time() -> None:
    before_verification = datetime(2026, 8, 16, 22, 18, tzinfo=UTC)
    base = build_acquisition_report(run_all(probe_network=False), now=before_verification)
    report = apply_additional_current_paths(base, now=before_verification)
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)

    assert all(path["slug"] != "lighter-funding-rate-rebate" for path in paths)
