from datetime import UTC, datetime

from crypto_auto_trade.airdrop_acquisition import build_acquisition_report
from crypto_auto_trade.airdrop_agents import run_all


def test_grvt_current_reward_scope_and_weights_are_explicit() -> None:
    report = build_acquisition_report(
        run_all(probe_network=False),
        now=datetime(2026, 8, 14, 12, 30, tzinfo=UTC),
    )
    grvt = next(action for action in report["actions"] if action["slug"] == "grvt")

    assert grvt["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert grvt["reward_scope"] == "PERPETUAL_TRADES_ONLY"
    assert grvt["weekly_activity_weights"] == {
        "trading_volume_pct": 50,
        "open_interest_pct": 15,
        "liquidity_provision_pct": 5,
        "liquidations_pct": 5,
        "tvl_pct": 5,
        "direct_referrals_pct": 20,
    }
    assert "spot" in str(grvt["known_cost_or_risk"]).lower()
    assert "0.0450%" in str(grvt["known_cost_or_risk"])
    assert "u.s." in str(grvt["known_cost_or_risk"]).lower()
    assert "perpetual" in str(grvt["next_action"]).lower()
    assert grvt["auto_executed"] is False

    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
