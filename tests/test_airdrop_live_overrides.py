from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_live_overrides import (
    OVERRIDE_TTL_DAYS,
    REYA_SIGNAL_VERIFIED_AT,
    REYA_TRADING_PRICING_VERIFIED_AT,
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


def _reya_report() -> dict[str, object]:
    return {
        "reward_path_count": 21,
        "approval_required_count": 19,
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "live_approved": False,
        "additional_approval_paths": [],
        "actions": [
            {
                "slug": "reya-trading",
                "evidence_source": "https://docs.reya.xyz/reya-token/reya-chain-points-faqs",
                "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
                "requires_user_approval": True,
                "requires_funds": True,
                "requires_wallet_signature": True,
                "requires_real_order": True,
                "requires_asset_move": False,
                "action_taken": "NONE",
                "auto_executed": False,
            }
        ],
    }


def test_standx_live_parameters_refine_approval_queue_without_execution() -> None:
    now = datetime(2026, 8, 15, 18, 29, tzinfo=UTC)
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
    assert action["live_parameters"]["pairs"]["SPCX-USD"]["max_maker_hours_per_hour"] == 1
    assert "maximum notional" in action["missing_approval"].lower()
    assert "do not place" in action["next_action"].lower()
    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["live_approved"] is False


def test_reya_trading_pricing_refines_cost_queue_without_execution() -> None:
    now = datetime(2026, 8, 15, 16, 21, tzinfo=UTC)
    report = apply_live_overrides(_reya_report(), now=now)
    action = report["actions"][0]
    fee_model = action["announced_fee_model"]

    assert report["live_override_count"] == 2
    assert action["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"
    assert action["requires_user_approval"] is True
    assert action["action_taken"] == "NONE"
    assert action["auto_executed"] is False
    assert fee_model["standard_taker_fee_bps"] == 3
    assert fee_model["previous_headline_taker_fee_bps"] == 4
    assert fee_model["lowest_rolling_30d_volume_taker_fee_bps"] == 2
    assert fee_model["orderbook_maker_fee_bps"] == 0
    assert fee_model["orderbook_maker_fee_effective_status"] == "ON_ORDERBOOK_LAUNCH"
    assert fee_model["maker_rebates_status"] == "TO_FOLLOW_AFTER_ORDERBOOK_LAUNCH"
    assert "pay-less-to-take-get-paid-to-make" in action["pricing_evidence_source"]
    assert "spread" in action["known_cost_or_risk"].lower()
    assert "actually active" in action["missing_approval"].lower()
    assert "do not assume announced future maker rebates are active" in action["next_action"].lower()
    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["live_approved"] is False


def test_reya_signal_is_blocked_when_no_current_open_submission_channel_is_verified() -> None:
    now = datetime(2026, 8, 15, 15, 23, tzinfo=UTC)
    report = apply_live_overrides(_reya_report(), now=now)
    paths = report["additional_review_paths"]
    assert isinstance(paths, list)
    signal = next(path for path in paths if path["slug"] == "reya-signal")

    assert report["live_override_count"] == 1
    assert report["reward_path_count"] == 22
    assert report["approval_required_count"] == 19
    assert report["verified_additional_review_path_count"] == 1
    assert report["nonfinancial_review_required_count"] == 0
    assert report["nonfinancial_blocked_no_open_channel_count"] == 1
    assert signal["acquisition_state"] == "NONFINANCIAL_REWARD_PATH_BLOCKED_NO_OPEN_CHANNEL"
    assert signal["requires_user_approval"] is False
    assert signal["requires_funds"] is False
    assert signal["requires_wallet_signature"] is False
    assert signal["requires_real_order"] is False
    assert signal["requires_asset_move"] is False
    assert signal["reward_deterministic"] is False
    assert signal["action_taken"] == "NONE"
    assert signal["auto_executed"] is False
    assert signal["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert signal["current_open_submission_verified"] is False
    assert signal["known_formal_channel_status"] == "APPLICATION_WINDOW_CLOSED"
    assert signal["known_application_deadline"] == "2026-04-01"
    assert "without trading or staking" in signal["evidence_note"].lower()
    assert "closed on april 1, 2026" in signal["evidence_note"].lower()
    assert "current official open" in signal["missing_approval"].lower()
    assert "expired genesis application" in signal["next_action"].lower()
    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["live_approved"] is False


def test_reya_signal_overlay_is_idempotent() -> None:
    now = datetime(2026, 8, 15, 15, 23, tzinfo=UTC)
    once = apply_live_overrides(_reya_report(), now=now)
    twice = apply_live_overrides(once, now=now)

    assert twice["reward_path_count"] == 22
    assert twice["nonfinancial_review_required_count"] == 0
    assert twice["nonfinancial_blocked_no_open_channel_count"] == 1
    assert sum(path["slug"] == "reya-signal" for path in twice["additional_review_paths"]) == 1


def test_standx_override_expires_closed() -> None:
    verified = datetime.fromisoformat(STANDX_MAKER_VERIFIED_AT).astimezone(UTC)
    stale = verified + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1)
    report = apply_live_overrides(_base_report(), now=stale)

    assert report["live_override_count"] == 0
    assert "live_parameters" not in report["actions"][0]


def test_reya_signal_review_path_expires_closed() -> None:
    signal_verified = datetime.fromisoformat(REYA_SIGNAL_VERIFIED_AT).astimezone(UTC)
    pricing_verified = datetime.fromisoformat(REYA_TRADING_PRICING_VERIFIED_AT).astimezone(UTC)
    stale = max(signal_verified, pricing_verified) + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1)
    report = apply_live_overrides(_reya_report(), now=stale)

    assert report["live_override_count"] == 0
    assert report["nonfinancial_review_required_count"] == 0
    assert report["nonfinancial_blocked_no_open_channel_count"] == 0
    assert report["verified_additional_review_path_count"] == 0
    assert report["reward_path_count"] == 21
    assert report["additional_review_paths"] == []
    assert "announced_fee_model" not in report["actions"][0]


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


def test_published_max_maker_hours_match_current_official_table() -> None:
    expected = {
        "BTC-USD": 10,
        "ETH-USD": 10,
        "XAG-USD": 2,
        "XAU-USD": 2,
        "CL-USD": 2,
        "HYPE-USD": 10,
        "BNB-USD": 10,
        "SOL-USD": 10,
        "TSLA-USD": 2,
        "SPCX-USD": 1,
        "MU-USD": 2,
    }
    actual = {
        pair: values["max_maker_hours_per_hour"]
        for pair, values in STANDX_MAKER_LIVE_PARAMETERS["pairs"].items()
    }
    assert actual == expected
