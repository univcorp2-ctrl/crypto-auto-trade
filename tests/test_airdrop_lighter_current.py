from datetime import UTC, datetime

from crypto_auto_trade.airdrop_acquisition import build_acquisition_report
from crypto_auto_trade.airdrop_agents import run_all


def _lighter_action() -> dict[str, object]:
    report = build_acquisition_report(
        run_all(probe_network=False),
        now=datetime(2026, 8, 14, 21, 30, tzinfo=UTC),
    )
    actions = report["actions"]
    assert isinstance(actions, list)
    return next(action for action in actions if action["slug"] == "lighter")


def test_lighter_current_retail_points_rules_are_explicitly_approval_gated() -> None:
    lighter = _lighter_action()

    assert lighter["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert lighter["requires_real_order"] is True
    assert lighter["requires_asset_move"] is False
    assert lighter["retail_weekly_points"] == 200000
    assert lighter["retail_activity_window"] == "WEDNESDAY_TO_TUESDAY"
    assert lighter["retail_activity_factors"] == [
        "volume",
        "open_interest",
        "fundings",
        "liquidations_and_deleverages",
        "pnl",
    ]
    assert "NONLINEAR" in str(lighter["retail_formula_characteristics"])
    assert "200,000" in str(lighter["evidence_note"])
    assert "intentionally losing" in str(lighter["known_cost_or_risk"]).lower()
    assert "solely to chase points" in str(lighter["missing_approval"]).lower()
    assert "do not increase leverage" in str(lighter["next_action"]).lower()
    assert "https://docs.lighter.xyz/points-program/retail" in lighter["evidence_sources"]
    assert "https://docs.lighter.xyz/perpetual-futures/api" in lighter["evidence_sources"]
