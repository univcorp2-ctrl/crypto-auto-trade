from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_acquisition import build_acquisition_report
from crypto_auto_trade.airdrop_additional_current_paths import apply_additional_current_paths
from crypto_auto_trade.airdrop_agents import run_all
from crypto_auto_trade.airdrop_decibel_claim_surface import (
    DECIBEL_CLAIM_SURFACE_VERIFIED_AT,
    DECIBEL_LIVE_CAMPAIGNS_SOURCE,
    DECIBEL_REWARDS_FAQ_SOURCE,
    DECIBEL_REWARDS_OVERVIEW_SOURCE,
    apply_decibel_claim_surface,
)

VERIFIED = datetime.fromisoformat(DECIBEL_CLAIM_SURFACE_VERIFIED_AT).astimezone(UTC)

CURRENT_TEXTS = {
    DECIBEL_LIVE_CAMPAIGNS_SOURCE: (
        "Active now — distributing rewards today. Review and claim all eligible rewards "
        "from the /rewards page in the Decibel app; you may also see Claim now pop-ups."
    ),
    DECIBEL_REWARDS_OVERVIEW_SOURCE: (
        "Campaign rewards are claimed through the /rewards page and credited directly to "
        "your trading account balance in a single onchain transaction."
    ),
    DECIBEL_REWARDS_FAQ_SOURCE: (
        "You'll see the expiry date on each tile in /rewards. New campaigns appear on the "
        "/rewards page."
    ),
}


def _report(now: datetime) -> dict[str, object]:
    base = build_acquisition_report(run_all(probe_network=False), now=now)
    return apply_additional_current_paths(base, now=now)


def _claim(report: dict[str, object]) -> dict[str, object]:
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)
    return next(path for path in paths if path["slug"] == "decibel-campaign-claims")


def test_current_decibel_docs_confirm_rewards_page_but_keep_claim_financially_gated() -> None:
    updated = apply_decibel_claim_surface(
        _report(VERIFIED),
        now=VERIFIED,
        source_texts=CURRENT_TEXTS,
        evidence_checked_at=VERIFIED,
    )
    claim = _claim(updated)

    assert updated["decibel_claim_surface_override_count"] == 1
    assert updated["decibel_claim_surface_live_recheck"] is True
    assert claim["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert (
        claim["claim_surface_status"]
        == "CURRENT_REWARDS_PAGE_AND_IN_APP_CLAIM_NOW_CONFIRMED"
    )
    assert (
        claim["claim_status"]
        == "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_REWARDS_PAGE_OR_IN_APP_NOTIFICATION"
    )
    assert claim["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert claim["requires_user_approval"] is True
    assert claim["requires_funds"] is False
    assert claim["requires_wallet_signature"] is True
    assert claim["requires_real_order"] is False
    assert claim["requires_asset_move"] is True
    assert claim["action_taken"] == "NONE"
    assert claim["auto_executed"] is False
    assert "review and claim rewards from the /rewards page" in str(
        claim["evidence_note"]
    ).lower()
    assert "single onchain transaction" in str(claim["evidence_note"]).lower()
    assert "already-authenticated decibel" in str(claim["next_action"]).lower()
    assert "do not connect/sign a wallet" in str(claim["next_action"]).lower()

    assert updated["financial_actions_executed"] == 0
    assert updated["asset_transfers_executed"] == 0
    assert updated["wallet_signatures_executed"] == 0
    assert updated["live_orders_executed"] == 0


def test_decibel_live_recheck_fails_closed_when_live_page_says_rewards_page_coming_soon() -> None:
    conflict = dict(CURRENT_TEXTS)
    conflict[DECIBEL_LIVE_CAMPAIGNS_SOURCE] = (
        "Active now — distributing rewards today. The /rewards page is coming soon. "
        "Use in-app Claim now pop-ups in the meantime."
    )

    updated = apply_decibel_claim_surface(
        _report(VERIFIED),
        now=VERIFIED,
        source_texts=conflict,
        evidence_checked_at=VERIFIED,
    )
    claim = _claim(updated)

    assert claim["evidence_status"] == "PRIMARY_VERIFIED_CURRENT_CONFLICT_FAIL_CLOSED"
    assert (
        claim["claim_surface_status"]
        == "CURRENT_IN_APP_CLAIM_NOW_CONFIRMED_REWARDS_PAGE_CONFLICT_UNVERIFIED"
    )
    assert "fails closed" in str(claim["evidence_note"]).lower()
    assert "current authenticated in-app" in str(claim["next_action"]).lower()
    assert claim["action_taken"] == "NONE"
    assert claim["auto_executed"] is False


def test_decibel_live_recheck_fails_closed_when_required_primary_source_is_missing() -> None:
    incomplete = dict(CURRENT_TEXTS)
    incomplete.pop(DECIBEL_REWARDS_FAQ_SOURCE)

    updated = apply_decibel_claim_surface(
        _report(VERIFIED),
        now=VERIFIED,
        source_texts=incomplete,
        evidence_checked_at=VERIFIED,
        fetch_errors={DECIBEL_REWARDS_FAQ_SOURCE: "TimeoutError: timed out"},
    )
    claim = _claim(updated)

    assert claim["evidence_status"] == "CURRENT_PRIMARY_RECHECK_INCOMPLETE_FAIL_CLOSED"
    assert claim["claim_surface_status"] == "REVERIFY_REQUIRED_CURRENT_CLAIM_SURFACE"
    assert updated["decibel_claim_surface_fetch_error_count"] == 1
    assert "re-fetch current decibel" in str(claim["next_action"]).lower()
    assert claim["action_taken"] == "NONE"
    assert claim["auto_executed"] is False


def test_decibel_snapshot_fallback_is_ttl_gated() -> None:
    before = VERIFIED - timedelta(seconds=1)
    old_report = _report(before)
    not_yet = apply_decibel_claim_surface(old_report, now=before)
    assert not_yet["decibel_claim_surface_override_count"] == 0

    stale = VERIFIED + timedelta(days=8)
    stale_report = _report(VERIFIED + timedelta(days=1))
    expired = apply_decibel_claim_surface(stale_report, now=stale)
    assert expired["decibel_claim_surface_override_count"] == 0
