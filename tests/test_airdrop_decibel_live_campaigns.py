from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS, build_acquisition_report
from crypto_auto_trade.airdrop_agents import run_all
from crypto_auto_trade.airdrop_decibel_live_campaigns import (
    DECIBEL_LIVE_CAMPAIGNS_VERIFIED_AT,
    apply_decibel_live_campaigns,
)

# This snapshot is intentionally TTL-gated because campaign parameters are dynamic.
VERIFIED = datetime.fromisoformat(DECIBEL_LIVE_CAMPAIGNS_VERIFIED_AT).astimezone(UTC)


def _base_report(*, now: datetime) -> dict[str, object]:
    return build_acquisition_report(run_all(probe_network=False), now=now)


def _path(report: dict[str, object], slug: str) -> dict[str, object]:
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)
    return next(path for path in paths if path["slug"] == slug)


def test_decibel_first_trade_and_maker_rebate_are_approval_only() -> None:
    current = VERIFIED + timedelta(seconds=1)
    result = apply_decibel_live_campaigns(_base_report(now=current), now=current)

    first_trade = _path(result, "decibel-first-trade-on-us")
    assert first_trade["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert first_trade["requires_user_approval"] is True
    assert first_trade["requires_funds"] is True
    assert first_trade["requires_wallet_signature"] is True
    assert first_trade["requires_real_order"] is True
    assert first_trade["requires_asset_move"] is True
    assert first_trade["deposit_usdc_min"] == 250
    assert first_trade["deposit_usdc_max"] == 5000
    assert first_trade["leverage_to_lock_days"] == {"20x": 1, "30x": 4, "40x": 7}
    assert first_trade["action_taken"] == "NONE"
    assert first_trade["auto_executed"] is False

    maker = _path(result, "decibel-maker-rebate")
    assert maker["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert maker["requires_user_approval"] is True
    assert maker["requires_funds"] is True
    assert maker["requires_real_order"] is True
    assert maker["maker_rebate_bps_direct_current"] == 0.5
    assert maker["minimum_maker_ratio_pct"] == 80
    assert maker["qualifying_order_type"] == "BULK_BATCH_MAKER_FILLS_ONLY"
    assert maker["monthly_cap_usd"] == 25000
    assert "0_25_BPS" in str(maker["source_conflict"])
    assert maker["action_taken"] == "NONE"
    assert maker["auto_executed"] is False

    assert result["reward_path_count"] == _base_report(now=current)["reward_path_count"] + 2
    assert result["additional_approval_required_count"] == _base_report(now=current)["additional_approval_required_count"] + 2
    assert result["approval_required_count"] == _base_report(now=current)["approval_required_count"] + 2
    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0
    assert result["auto_executed_action_count"] == 0


def test_decibel_campaign_exclusions_are_fail_closed() -> None:
    current = VERIFIED + timedelta(seconds=1)
    result = apply_decibel_live_campaigns(_base_report(now=current), now=current)
    exclusions = result["campaign_exclusions"]
    assert isinstance(exclusions, list)
    by_slug = {item["slug"]: item for item in exclusions}
    assert by_slug["decibel-global-warming-home-cooling"]["state"] == "EXCLUDED_DATE_CONFLICT"
    assert by_slug["decibel-liquidation-rebate-qualification"]["state"] == "EXCLUDED_HARMFUL_QUALIFICATION"


def test_decibel_live_campaign_paths_are_idempotent_and_ttl_gated() -> None:
    current = VERIFIED + timedelta(seconds=1)
    once = apply_decibel_live_campaigns(_base_report(now=current), now=current)
    twice = apply_decibel_live_campaigns(once, now=current)
    for slug in ("decibel-first-trade-on-us", "decibel-maker-rebate"):
        assert sum(path.get("slug") == slug for path in twice["additional_approval_paths"]) == 1
    assert twice["reward_path_count"] == once["reward_path_count"]
    assert twice["approval_required_count"] == once["approval_required_count"]

    before = apply_decibel_live_campaigns(_base_report(now=VERIFIED - timedelta(seconds=1)), now=VERIFIED - timedelta(seconds=1))
    stale_time = VERIFIED + timedelta(days=VERIFICATION_TTL_DAYS, seconds=1)
    stale = apply_decibel_live_campaigns(_base_report(now=stale_time), now=stale_time)
    for report in (before, stale):
        slugs = {path.get("slug") for path in report["additional_approval_paths"]}
        assert "decibel-first-trade-on-us" not in slugs
        assert "decibel-maker-rebate" not in slugs
