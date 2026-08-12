from crypto_auto_trade.airdrop_acquisition import build_acquisition_report
from crypto_auto_trade.airdrop_agents import run_all


def _action(report: dict[str, object], slug: str) -> dict[str, object]:
    actions = report["actions"]
    assert isinstance(actions, list)
    return next(action for action in actions if action["slug"] == slug)


def test_acquisition_cycle_never_executes_financial_side_effects() -> None:
    status = run_all(probe_network=False)
    report = build_acquisition_report(status)

    assert report["mode"] == "ACQUISITION_GATED"
    assert report["target_count"] == 20
    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["live_approved"] is False


def test_verified_wave_one_trading_targets_go_to_approval_queue() -> None:
    report = build_acquisition_report(run_all(probe_network=False))

    pacifica = _action(report, "pacifica")
    hibachi = _action(report, "hibachi")

    assert pacifica["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert pacifica["requires_user_approval"] is True
    assert pacifica["requires_funds"] is True
    assert pacifica["requires_wallet_signature"] is True

    assert hibachi["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert hibachi["requires_user_approval"] is True
    assert hibachi["requires_funds"] is True


def test_current_primary_source_wave_two_promotions_are_approval_only() -> None:
    report = build_acquisition_report(run_all(probe_network=False))

    for slug in ("standx-maker", "standx-position", "decibel-trading", "grvt"):
        action = _action(report, slug)
        assert action["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
        assert action["requires_user_approval"] is True
        assert action["requires_funds"] is True
        assert action["verification_sources"]
        assert action["known_cost_risk"]
        assert action["missing_approval"]

    liquidity = _action(report, "decibel-liquidity")
    assert liquidity["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert liquidity["requires_user_approval"] is True
    assert liquidity["requires_wallet_signature"] is True


def test_unverified_wave_one_targets_stay_blocked() -> None:
    report = build_acquisition_report(run_all(probe_network=False))

    assert _action(report, "kyan")["acquisition_state"] == "BLOCKED_UNVERIFIED"
    assert _action(report, "lighter")["acquisition_state"] == "BLOCKED_UNVERIFIED"


def test_current_queue_breakdown_is_explicit() -> None:
    report = build_acquisition_report(run_all(probe_network=False))

    assert report["current_verified_earning_path_count"] == 5
    assert report["approval_required_count"] == 7
    assert report["blocked_unverified_count"] == 2
    assert report["discovery_only_count"] == 1
    assert report["reverify_required_count"] == 10


def test_current_registry_does_not_claim_reward_actions_were_executed() -> None:
    report = build_acquisition_report(run_all(probe_network=False))

    assert report["safe_auto_adapter_count"] == 0
    assert report["auto_executed_action_count"] == 0
    assert all(action["action_taken"] == "NONE" for action in report["actions"])
