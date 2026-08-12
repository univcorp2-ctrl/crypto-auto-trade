from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS, build_acquisition_report
from crypto_auto_trade.airdrop_agents import run_all

TEST_NOW = datetime(2026, 8, 12, 4, 0, tzinfo=UTC)


def _report(*, now: datetime = TEST_NOW) -> dict[str, object]:
    return build_acquisition_report(run_all(probe_network=False), now=now)


def _action(report: dict[str, object], slug: str) -> dict[str, object]:
    actions = report["actions"]
    assert isinstance(actions, list)
    return next(action for action in actions if action["slug"] == slug)


def test_acquisition_cycle_never_executes_financial_side_effects() -> None:
    report = _report()

    assert report["mode"] == "ACQUISITION_GATED"
    assert report["target_count"] == 20
    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["live_approved"] is False


def test_verified_wave_one_trading_targets_go_to_approval_queue() -> None:
    report = _report()

    pacifica = _action(report, "pacifica")
    hibachi = _action(report, "hibachi")

    assert pacifica["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert pacifica["requires_user_approval"] is True
    assert pacifica["requires_funds"] is True
    assert pacifica["requires_wallet_signature"] is True
    assert pacifica["requires_real_order"] is True

    assert hibachi["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert hibachi["requires_user_approval"] is True
    assert hibachi["requires_funds"] is True
    assert hibachi["requires_real_order"] is True


def test_primary_verified_wave_two_targets_move_to_exact_approval_queues() -> None:
    report = _report()

    standx = _action(report, "standx-maker")
    decibel_trading = _action(report, "decibel-trading")
    decibel_liquidity = _action(report, "decibel-liquidity")
    grvt = _action(report, "grvt")

    assert standx["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert standx["requires_real_order"] is True
    assert standx["authentication_recheck_required"] is True
    assert standx["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert decibel_trading["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert decibel_trading["requires_real_order"] is True
    assert decibel_trading["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert decibel_liquidity["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert decibel_liquidity["requires_asset_move"] is True
    assert decibel_liquidity["requires_funds"] is True
    assert decibel_liquidity["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert grvt["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert grvt["requires_real_order"] is True
    assert grvt["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "0.0450%" in str(grvt["known_cost_or_risk"])


def test_verified_gated_evidence_expires_back_to_reverify() -> None:
    stale_now = TEST_NOW + timedelta(days=VERIFICATION_TTL_DAYS + 1)
    report = _report(now=stale_now)

    assert _action(report, "standx-maker")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "decibel-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "decibel-liquidity")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "grvt")["acquisition_state"] == "REVERIFY_REQUIRED"


def test_unverified_wave_one_targets_stay_blocked() -> None:
    report = _report()

    assert _action(report, "kyan")["acquisition_state"] == "BLOCKED_UNVERIFIED"
    assert _action(report, "lighter")["acquisition_state"] == "BLOCKED_UNVERIFIED"


def test_current_queue_breakdown_is_explicit() -> None:
    report = _report()

    assert report["verified_gated_action_count"] == 4
    assert report["approval_required_count"] == 6
    assert report["blocked_unverified_count"] == 2
    assert report["discovery_only_count"] == 1
    assert report["reverify_required_count"] == 11


def test_current_registry_does_not_claim_reward_actions_were_executed() -> None:
    report = _report()

    assert report["safe_auto_adapter_count"] == 0
    assert report["auto_executed_action_count"] == 0
    assert all(action["action_taken"] == "NONE" for action in report["actions"])
