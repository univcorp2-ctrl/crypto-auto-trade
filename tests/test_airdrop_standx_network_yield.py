from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS, build_acquisition_report
from crypto_auto_trade.airdrop_additional_current_paths import (
    STANDX_NETWORK_YIELD_VERIFIED_AT,
    apply_additional_current_paths,
)
from crypto_auto_trade.airdrop_agents import run_all

NOW = datetime(2026, 8, 15, 17, 30, tzinfo=UTC)


def _base_report() -> dict[str, object]:
    return build_acquisition_report(run_all(probe_network=False), now=NOW)


def _path(report: dict[str, object]) -> dict[str, object]:
    paths = report["additional_approval_paths"]
    assert isinstance(paths, list)
    return next(path for path in paths if path["slug"] == "standx-network-yield")


def test_standx_network_yield_adds_approval_only_path() -> None:
    base = _base_report()
    result = apply_additional_current_paths(base, now=NOW)
    path = _path(result)

    assert path["parent_slug"] == "standx-maker"
    assert path["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert path["requires_user_approval"] is True
    assert path["requires_funds"] is True
    assert path["requires_real_order"] is True
    assert path["requires_asset_move"] is False
    assert path["auto_executed"] is False
    assert path["action_taken"] == "NONE"
    assert path["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "500,000 DUSD" in str(path["evidence_note"])
    assert "+5% bonus" in str(path["evidence_note"])
    assert "self-referral" in str(path["known_cost_or_risk"]).lower()

    assert result["reward_path_count"] == base["reward_path_count"] + 1
    assert result["verified_additional_path_count"] == base["verified_additional_path_count"] + 1
    assert result["additional_approval_required_count"] == base["additional_approval_required_count"] + 1
    assert result["approval_required_count"] == base["approval_required_count"] + 1

    assert result["financial_actions_executed"] == 0
    assert result["asset_transfers_executed"] == 0
    assert result["wallet_signatures_executed"] == 0
    assert result["live_orders_executed"] == 0


def test_standx_network_yield_is_idempotent() -> None:
    once = apply_additional_current_paths(_base_report(), now=NOW)
    twice = apply_additional_current_paths(once, now=NOW)

    paths = twice["additional_approval_paths"]
    assert isinstance(paths, list)
    assert sum(path.get("slug") == "standx-network-yield" for path in paths if isinstance(path, dict)) == 1
    assert twice["reward_path_count"] == once["reward_path_count"]
    assert twice["approval_required_count"] == once["approval_required_count"]


def test_standx_network_yield_future_or_stale_evidence_is_not_applied() -> None:
    verified = datetime.fromisoformat(STANDX_NETWORK_YIELD_VERIFIED_AT).astimezone(UTC)

    before = apply_additional_current_paths(_base_report(), now=verified - timedelta(seconds=1))
    stale = apply_additional_current_paths(
        _base_report(),
        now=verified + timedelta(days=VERIFICATION_TTL_DAYS, seconds=1),
    )

    for report in (before, stale):
        paths = report["additional_approval_paths"]
        assert isinstance(paths, list)
        assert all(path.get("slug") != "standx-network-yield" for path in paths if isinstance(path, dict))
