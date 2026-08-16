from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_acquisition import build_acquisition_report
from crypto_auto_trade.airdrop_additional_current_paths import apply_additional_current_paths
from crypto_auto_trade.airdrop_agents import run_all
from crypto_auto_trade.airdrop_decibel_claim_surface import (
    DECIBEL_CLAIM_SURFACE_VERIFIED_AT,
    apply_decibel_claim_surface,
)

VERIFIED = datetime.fromisoformat(DECIBEL_CLAIM_SURFACE_VERIFIED_AT).astimezone(UTC)


def _report(now: datetime) -> dict[str, object]:
    base = build_acquisition_report(run_all(probe_network=False), now=now)
    return apply_additional_current_paths(base, now=now)


def _claim(report: dict[str, object]) -> dict[str, object]:
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)
    return next(path for path in paths if path["slug"] == "decibel-campaign-claims")


def test_current_decibel_claim_route_uses_in_app_notification_until_rewards_page_is_live() -> None:
    current = VERIFIED + timedelta(seconds=1)
    updated = apply_decibel_claim_surface(_report(current), now=current)
    claim = _claim(updated)

    assert updated["decibel_claim_surface_override_count"] == 1
    assert claim["claim_surface_status"] == "CURRENT_IN_APP_CLAIM_NOW_CONFIRMED_REWARDS_PAGE_COMING_SOON_UNCONFIRMED"
    assert claim["claim_status"] == "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_IN_APP_CLAIM_NOTIFICATION"
    assert claim["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert claim["requires_user_approval"] is True
    assert claim["requires_funds"] is False
    assert claim["requires_wallet_signature"] is True
    assert claim["requires_real_order"] is False
    assert claim["requires_asset_move"] is True
    assert claim["action_taken"] == "NONE"
    assert claim["auto_executed"] is False
    assert "coming soon" in str(claim["evidence_note"]).lower()
    assert "claim now" in str(claim["evidence_note"]).lower()
    assert "must not be treated as a current claim surface" in str(claim["missing_approval"]).lower()
    assert "authenticated account also exposes a functional /rewards page" in str(claim["next_action"]).lower()
    assert "do not connect/sign a wallet" in str(claim["next_action"]).lower()

    assert updated["financial_actions_executed"] == 0
    assert updated["asset_transfers_executed"] == 0
    assert updated["wallet_signatures_executed"] == 0
    assert updated["live_orders_executed"] == 0


def test_decibel_claim_surface_override_is_ttl_gated() -> None:
    before = VERIFIED - timedelta(seconds=1)
    old_report = _report(before)
    not_yet = apply_decibel_claim_surface(old_report, now=before)
    assert not_yet["decibel_claim_surface_override_count"] == 0

    stale = VERIFIED + timedelta(days=8)
    stale_report = _report(VERIFIED + timedelta(days=1))
    expired = apply_decibel_claim_surface(stale_report, now=stale)
    assert expired["decibel_claim_surface_override_count"] == 0
