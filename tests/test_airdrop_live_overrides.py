from datetime import UTC, datetime, timedelta

from crypto_auto_trade.airdrop_live_overrides import (
    OVERRIDE_TTL_DAYS,
    REYA_SIGNAL_VERIFIED_AT,
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


def test_reya_signal_is_tracked_as_nonfinancial_review_path_without_execution() -> None:
    now = datetime(2026, 8, 15, 4, 21, tzinfo=UTC)
    report = apply_live_overrides(_reya_report(), now=now)
    paths = report["additional_review_paths"]
    assert isinstance(paths, list)
    signal = next(path for path in paths if path["slug"] == "reya-signal")

    assert report["live_override_count"] == 1
    assert report["reward_path_count"] == 22
    assert report["approval_required_count"] == 19
    assert report["verified_additional_review_path_count"] == 1
    assert report["nonfinancial_review_required_count"] == 1
    assert signal["acquisition_state"] == "NONFINANCIAL_REWARD_PATH_REVIEW_REQUIRED"
    assert signal["requires_user_approval"] is False
    assert signal["requires_funds"] is False
    assert signal["requires_wallet_signature"] is False
    assert signal["requires_real_order"] is False
    assert signal["requires_asset_move"] is False
    assert signal["reward_deterministic"] is False
    assert signal["action_taken"] == "NONE"
    assert signal["auto_executed"] is False
    assert signal["evidence_status"] == "PRIMARY_VERIFIED_CURRENT"
    assert "without trading or staking" in signal["evidence_note"].lower()
    assert "submission" in signal["missing_approval"].lower()
    assert "do not auto-post" in signal["next_action"].lower()
    assert report["financial_actions_executed"] == 0
    assert report["asset_transfers_executed"] == 0
    assert report["wallet_signatures_executed"] == 0
    assert report["live_orders_executed"] == 0
    assert report["live_approved"] is False


def test_reya_signal_overlay_is_idempotent() -> None:
    now = datetime(2026, 8, 15, 4, 21, tzinfo=UTC)
    once = apply_live_overrides(_reya_report(), now=now)
    twice = apply_live_overrides(once, now=now)

    assert twice["reward_path_count"] == 22
    assert twice["nonfinancial_review_required_count"] == 1
    assert sum(path["slug"] == "reya-signal" for path in twice["additional_review_paths"]) == 1


def test_standx_override_expires_closed() -> None:
    verified = datetime.fromisoformat(STANDX_MAKER_VERIFIED_AT).astimezone(UTC)
    stale = verified + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1)
    report = apply_live_overrides(_base_report(), now=stale)

    assert report["live_override_count"] == 0
    assert "live_parameters" not in report["actions"][0]


def test_reya_signal_review_path_expires_closed() -> None:
    verified = datetime.fromisoformat(REYA_SIGNAL_VERIFIED_AT).astimezone(UTC)
    stale = verified + timedelta(days=OVERRIDE_TTL_DAYS, seconds=1)
    report = apply_live_overrides(_reya_report(), now=stale)

    assert report["live_override_count"] == 0
    assert report["nonfinancial_review_required_count"] == 0
    assert report["verified_additional_review_path_count"] == 0
    assert report["reward_path_count"] == 21
    assert report["additional_review_paths"] == []


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
