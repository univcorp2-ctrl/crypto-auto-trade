from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS, build_acquisition_report
from crypto_auto_trade.airdrop_agents import run_all

TEST_NOW = datetime(2026, 8, 14, 9, 25, tzinfo=UTC)


def _report(*, now: datetime = TEST_NOW) -> dict[str, object]:
    return build_acquisition_report(run_all(probe_network=False), now=now)


def _action(report: dict[str, object], slug: str) -> dict[str, object]:
    actions = report["actions"]
    assert isinstance(actions, list)
    return next(action for action in actions if action["slug"] == slug)


def _additional_path(report: dict[str, object], slug: str) -> dict[str, object]:
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)
    return next(path for path in paths if path["slug"] == slug)


def test_acquisition_cycle_never_executes_financial_side_effects() -> None:
    report = _report()

    assert report["mode"] == "ACQUISITION_GATED"
    assert report["target_count"] == 20
    assert report["reward_path_count"] == 21
    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["live_approved"] is False


def test_verified_wave_one_trading_targets_go_to_approval_queue() -> None:
    report = _report()

    pacifica = _action(report, "pacifica")
    hibachi = _action(report, "hibachi")
    kyan = _action(report, "kyan")
    lighter = _action(report, "lighter")

    assert pacifica["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert pacifica["requires_user_approval"] is True
    assert pacifica["requires_funds"] is True
    assert pacifica["requires_wallet_signature"] is True
    assert pacifica["requires_real_order"] is True

    assert hibachi["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert hibachi["requires_user_approval"] is True
    assert hibachi["requires_funds"] is True
    assert hibachi["requires_real_order"] is True

    assert kyan["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert kyan["requires_user_approval"] is True
    assert kyan["requires_funds"] is True
    assert kyan["requires_wallet_signature"] is True
    assert kyan["requires_real_order"] is True
    assert kyan["evidence_basis"] == "PRIMARY_DOCS_CHANNEL_NEUTRAL_INFERENCE"

    assert lighter["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert lighter["requires_user_approval"] is True
    assert lighter["requires_funds"] is True
    assert lighter["requires_real_order"] is True
    assert lighter["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"


def test_primary_verified_targets_move_to_exact_approval_queues() -> None:
    report = _report()

    hyprearn = _action(report, "hyprearn")
    standx_maker = _action(report, "standx-maker")
    standx_position = _action(report, "standx-position")
    decibel_trading = _action(report, "decibel-trading")
    decibel_liquidity = _action(report, "decibel-liquidity")
    grvt = _action(report, "grvt")
    lighter = _action(report, "lighter")
    nado_trading = _action(report, "nado-trading")
    nado_nlp = _action(report, "nado-nlp")
    kyan = _action(report, "kyan")
    ethereal_trading = _action(report, "ethereal-trading")
    ethereal_margin = _action(report, "ethereal-margin")
    reya_trading = _action(report, "reya-trading")
    reya_staking = _action(report, "reya-staking")
    extended_trading = _action(report, "extended-trading")
    extended_liquidity = _action(report, "extended-liquidity")

    assert hyprearn["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert hyprearn["requires_asset_move"] is True
    assert hyprearn["requires_real_order"] is True
    assert hyprearn["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert standx_maker["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert standx_maker["requires_real_order"] is True
    assert standx_maker["authentication_recheck_required"] is True
    assert standx_maker["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert standx_position["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert standx_position["requires_real_order"] is True
    assert standx_position["requires_funds"] is True
    assert standx_position["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

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

    assert lighter["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert lighter["requires_real_order"] is True
    assert lighter["requires_asset_move"] is False
    assert lighter["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "self-trading" in str(lighter["next_action"]).lower()

    assert nado_trading["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert nado_trading["requires_real_order"] is True
    assert nado_trading["requires_asset_move"] is False
    assert nado_trading["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "wash" in str(nado_trading["next_action"]).lower()

    assert nado_nlp["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert nado_nlp["requires_asset_move"] is True
    assert nado_nlp["requires_real_order"] is False
    assert nado_nlp["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert kyan["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert kyan["requires_real_order"] is True
    assert kyan["requires_wallet_signature"] is True
    assert kyan["requires_asset_move"] is False
    assert kyan["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert kyan["evidence_basis"] == "PRIMARY_DOCS_CHANNEL_NEUTRAL_INFERENCE"

    assert ethereal_trading["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert ethereal_trading["requires_real_order"] is True
    assert ethereal_trading["requires_wallet_signature"] is True
    assert ethereal_trading["requires_asset_move"] is False
    assert ethereal_trading["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert ethereal_trading["evidence_basis"] == "PRIMARY_DOCS_CHANNEL_NEUTRAL_INFERENCE"

    assert ethereal_margin["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert ethereal_margin["requires_asset_move"] is True
    assert ethereal_margin["requires_real_order"] is False
    assert ethereal_margin["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert reya_trading["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert reya_trading["requires_real_order"] is True
    assert reya_trading["requires_wallet_signature"] is True
    assert reya_trading["requires_asset_move"] is False
    assert reya_trading["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert reya_trading["evidence_basis"] == "PRIMARY_DOCS_CHANNEL_NEUTRAL_INFERENCE"

    assert reya_staking["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert reya_staking["requires_asset_move"] is True
    assert reya_staking["requires_real_order"] is False
    assert reya_staking["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert extended_trading["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert extended_trading["requires_real_order"] is True
    assert extended_trading["requires_asset_move"] is False
    assert extended_trading["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"

    assert extended_liquidity["acquisition_state"] == "APPROVAL_REQUIRED_ASSET_MOVE"
    assert extended_liquidity["requires_asset_move"] is True
    assert extended_liquidity["requires_real_order"] is False
    assert extended_liquidity["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"


def test_channel_neutral_api_trading_paths_are_inference_gated() -> None:
    report = _report()

    kyan = _action(report, "kyan")
    reya = _action(report, "reya-trading")
    ethereal = _action(report, "ethereal-trading")

    for action in (kyan, reya, ethereal):
        assert action["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
        assert action["requires_user_approval"] is True
        assert action["requires_wallet_signature"] is True
        assert action["evidence_basis"] == "PRIMARY_DOCS_CHANNEL_NEUTRAL_INFERENCE"
        assert "inference" in str(action["evidence_note"]).lower()


def test_n1_og_badge_is_safe_but_authentication_gated() -> None:
    report = _report()
    n1_badge = _action(report, "exchange01")

    assert n1_badge["acquisition_state"] == "SAFE_ACTION_AUTH_REQUIRED"
    assert n1_badge["requires_user_approval"] is False
    assert n1_badge["requires_funds"] is False
    assert n1_badge["requires_wallet_signature"] is False
    assert n1_badge["requires_real_order"] is False
    assert n1_badge["requires_asset_move"] is False
    assert n1_badge["authentication_recheck_required"] is True
    assert n1_badge["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "Discord" in str(n1_badge["evidence_note"])
    assert "do not connect a wallet" in str(n1_badge["next_action"]).lower()


def test_n1_points_launch_adds_financial_approval_path_without_overwriting_badge_path() -> None:
    report = _report()
    n1_badge = _action(report, "exchange01")
    n1_points = _additional_path(report, "n1-points-trading")

    assert n1_badge["acquisition_state"] == "SAFE_ACTION_AUTH_REQUIRED"
    assert n1_points["parent_slug"] == "exchange01"
    assert n1_points["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert n1_points["requires_user_approval"] is True
    assert n1_points["requires_funds"] is True
    assert n1_points["requires_real_order"] is True
    assert n1_points["requires_asset_move"] is False
    assert n1_points["auto_executed"] is False
    assert n1_points["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "75 million" in str(n1_points["evidence_note"])
    assert "exact" in str(n1_points["missing_approval"]).lower()


def test_future_dated_verification_does_not_become_current() -> None:
    before_new_verification = datetime(2026, 8, 12, 5, 20, tzinfo=UTC)
    report = _report(now=before_new_verification)

    assert _action(report, "lighter")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "nado-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "nado-nlp")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "kyan")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "exchange01")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "ethereal-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "ethereal-margin")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "reya-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "reya-staking")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "extended-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "extended-liquidity")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert report["additional_approval_required_count"] == 0


def test_verified_gated_evidence_expires_back_to_reverify() -> None:
    stale_now = TEST_NOW + timedelta(days=VERIFICATION_TTL_DAYS + 1)
    report = _report(now=stale_now)

    assert _action(report, "hyprearn")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "standx-maker")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "standx-position")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "decibel-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "decibel-liquidity")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "grvt")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "lighter")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "nado-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "nado-nlp")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "kyan")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "exchange01")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "ethereal-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "ethereal-margin")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "reya-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "reya-staking")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "extended-trading")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert _action(report, "extended-liquidity")["acquisition_state"] == "REVERIFY_REQUIRED"
    assert report["additional_approval_required_count"] == 0


def test_current_queue_breakdown_is_explicit() -> None:
    report = _report()

    assert report["verified_gated_action_count"] == 17
    assert report["verified_additional_path_count"] == 1
    assert report["safe_auth_required_count"] == 1
    assert report["primary_approval_required_count"] == 18
    assert report["additional_approval_required_count"] == 1
    assert report["approval_required_count"] == 19
    assert report["blocked_unverified_count"] == 0
    assert report["discovery_only_count"] == 1
    assert report["reverify_required_count"] == 0


def test_current_registry_does_not_claim_reward_actions_were_executed() -> None:
    report = _report()

    assert report["safe_auto_adapter_count"] == 0
    assert report["auto_executed_action_count"] == 0
    assert all(action["action_taken"] == "NONE" for action in report["actions"])
    assert all(path["action_taken"] == "NONE" for path in report["additional_approval_paths"])
