from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS, build_acquisition_report
from crypto_auto_trade.airdrop_agents import run_all
from crypto_auto_trade.airdrop_standx_maker_points import (
    STANDX_MAKER_POINTS_VERIFIED_AT,
    apply_standx_maker_points_path,
)

NOW = datetime(2026, 8, 17, 11, 25, tzinfo=UTC)


def _base_report() -> dict[str, object]:
    return build_acquisition_report(run_all(probe_network=False), now=NOW)


def _path(report: dict[str, object]) -> dict[str, object]:
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)
    return next(path for path in paths if path["slug"] == "standx-maker-points")


def test_standx_maker_points_adds_financial_approval_path_only() -> None:
    base = _base_report()
    result = apply_standx_maker_points_path(base, now=NOW)
    path = _path(result)

    assert path["parent_slug"] == "standx-maker"
    assert path["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert path["requires_user_approval"] is True
    assert path["requires_funds"] is True
    assert path["requires_real_order"] is True
    assert path["requires_wallet_signature"] is True
    assert path["requires_asset_move"] is False
    assert path["auto_executed"] is False
    assert path["action_taken"] == "NONE"
    assert path["evidence_status"] == "PRIMARY_VERIFIED_CURRENT_ACTION_CLASS_SCORING_RECHECK_REQUIRED"
    assert "Maker Points" in str(path["evidence_note"])
    assert "real limit orders" in str(path["known_cost_or_risk"])
    assert "quote-stuff" in str(path["next_action"]).lower()

    assert result["reward_path_count"] == base["reward_path_count"] + 1
    assert result["verified_additional_path_count"] == base["verified_additional_path_count"] + 1
    assert result["additional_approval_required_count"] == base["additional_approval_required_count"] + 1
    assert result["approval_required_count"] == base["approval_required_count"] + 1

    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0


def test_standx_maker_points_path_is_idempotent() -> None:
    once = apply_standx_maker_points_path(_base_report(), now=NOW)
    twice = apply_standx_maker_points_path(once, now=NOW)

    paths = twice["additional_approval_paths"]
    assert isinstance(paths, list)
    assert sum(path.get("slug") == "standx-maker-points" for path in paths if isinstance(path, dict)) == 1
    assert twice["reward_path_count"] == once["reward_path_count"]
    assert twice["approval_required_count"] == once["approval_required_count"]


def test_standx_maker_points_future_or_stale_evidence_is_not_applied() -> None:
    verified = datetime.fromisoformat(STANDX_MAKER_POINTS_VERIFIED_AT).astimezone(UTC)

    before = apply_standx_maker_points_path(_base_report(), now=verified - timedelta(seconds=1))
    stale = apply_standx_maker_points_path(
        _base_report(),
        now=verified + timedelta(days=VERIFICATION_TTL_DAYS, seconds=1),
    )

    for report in (before, stale):
        paths = report["additional_approval_paths"]
        assert isinstance(paths, list)
        assert all(path.get("slug") != "standx-maker-points" for path in paths if isinstance(path, dict))
