from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_live_overrides import (
    OVERRIDE_TTL_DAYS,
    STANDX_MAKER_LIVE_PARAMETERS,
    STANDX_MAKER_VERIFIED_AT,
    apply_live_overrides,
)


def _base_report() -> dict[str, object]:
    return {
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "live_approved": False,
        "actions": [
            {
                "slug": "standx-maker",
                "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
                "requires_user_approval": True,
                "requires_funds": True,
                "requires_real_order": True,
                "requires_asset_move": False,
                "action_taken": "NONE",
                "auto_executed": False,
            }
        ],
    }


def test_standx_live_parameters_refine_approval_queue_without_execution() -> None:
    now = datetime(2026, 8, 15, 3, 30, tzinfo=UTC)
    report = apply_live_overrides(_base_report(), now=now)
    action = report["actions"][0]

    assert report["live_override_count"] == 1
    assert action["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert action["requires_user_approval"] is True
    assert action["action_taken"] == "NONE"
    assert action["auto_executed"] is False
    assert action["live_parameters"]["qualifying_band_bps"] == 10
    assert action["live_parameters"]["uptime_tiers"]["standard"]["minimum_minutes_per_hour"] == 30
    assert action["live_parameters"]["uptime_tiers"]["boosted"]["minimum_minutes_per_hour"] == 42
    assert action["live_parameters"]["proximity_weights_pct"]["0_bps"] == 200
    assert action["live_parameters"]["pairs"]["BTC-USD"]["session"] == "24/7"
    assert action["live_parameters"]["pairs"]["XAU-USD"]["off_session_multiplier_pct"] == 10
    assert "maximum notional" in action["missing_approval"].lower()
    assert "do not place" in action["next_action"].lower()
    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["live_approved"] is False


def test_standx_override_expires_closed() -> None:
    verified = datetime.fromisoformat(STANDX_MAKER_VERIFIED_AT).astimezone(UTC)
    stale = verified + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1)
    report = apply_live_overrides(_base_report(), now=stale)

    assert report["live_override_count"] == 0
    assert "live_parameters" not in report["actions"][0]


def test_published_pair_table_is_complete_for_current_official_page() -> None:
    assert set(STANDX_MAKER_LIVE_PARAMETERS["pairs"]) == {
        "BTC-USD",
        "ETH-USD",
        "XAG-USD",
        "XAU-USD",
        "CL-USD",
        "HYPE-USD",
        "BNB-USD",
        "SOL-USD",
        "TSLA-USD",
        "SPCX-USD",
        "MU-USD",
    }
