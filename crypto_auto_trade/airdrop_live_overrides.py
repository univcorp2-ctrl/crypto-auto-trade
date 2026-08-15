from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

STANDX_MAKER_VERIFIED_AT = "2026-08-15T06:43:29+00:00"
STANDX_MAKER_EVIDENCE_SOURCE = "https://docs.standx.com/docs/standx-perps-solutions/community-maker-yield"
REYA_SIGNAL_VERIFIED_AT = "2026-08-15T15:22:00+00:00"
REYA_SIGNAL_EVIDENCE_SOURCE = "https://docs.reya.xyz/reya-token/reya-chain-points-faqs"
REYA_SIGNAL_AMBASSADOR_SOURCE = "https://blog.reya.network/introducing-the-reya-ambassador-program/"
REYA_SIGNAL_BLOG_INDEX_SOURCE = "https://blog.reya.network/"
REYA_SIGNAL_CORROBORATION_SOURCE = "https://cryptorank.io/drophunting/voltz-labs-activity87"
OVERRIDE_TTL_DAYS = 7

STANDX_MAKER_LIVE_PARAMETERS: dict[str, Any] = {
    "qualifying_band_bps": 10,
    "trading_session_timezone": "America/New_York",
    "uptime_tiers": {
        "standard": {"minimum_minutes_per_hour": 30, "multiplier": 0.5},
        "boosted": {"minimum_minutes_per_hour": 42, "multiplier": 1.0},
    },
    "proximity_weights_pct": {
        "0_bps": 200,
        "5_bps": 80,
        "10_bps": 40,
    },
    "pairs": {
        "BTC-USD": {"unit_size": 2, "per_side_cap": 20, "max_maker_hours_per_hour": 10, "session": "24/7", "off_session_multiplier_pct": None},
        "ETH-USD": {"unit_size": 60, "per_side_cap": 600, "max_maker_hours_per_hour": 10, "session": "24/7", "off_session_multiplier_pct": None},
        "XAG-USD": {"unit_size": 1500, "per_side_cap": 3000, "max_maker_hours_per_hour": 2, "session": "Sunday-Friday 18:00-17:00 next day ET", "off_session_multiplier_pct": 10},
        "XAU-USD": {"unit_size": 30, "per_side_cap": 60, "max_maker_hours_per_hour": 2, "session": "Sunday-Friday 18:00-17:00 next day ET", "off_session_multiplier_pct": 10},
        "CL-USD": {"unit_size": 1400, "per_side_cap": 2800, "max_maker_hours_per_hour": 2, "session": "Sunday-Friday 18:00-17:00 next day ET", "off_session_multiplier_pct": 10},
        "HYPE-USD": {"unit_size": 4000, "per_side_cap": 40000, "max_maker_hours_per_hour": 10, "session": "24/7", "off_session_multiplier_pct": None},
        "BNB-USD": {"unit_size": 300, "per_side_cap": 3000, "max_maker_hours_per_hour": 10, "session": "24/7", "off_session_multiplier_pct": None},
        "SOL-USD": {"unit_size": 1500, "per_side_cap": 15000, "max_maker_hours_per_hour": 10, "session": "24/7", "off_session_multiplier_pct": None},
        "TSLA-USD": {"unit_size": 400, "per_side_cap": 800, "max_maker_hours_per_hour": 2, "session": "US equity session", "off_session_multiplier_pct": 10},
        "SPCX-USD": {"unit_size": 800, "per_side_cap": 800, "max_maker_hours_per_hour": 2, "session": "US equity session", "off_session_multiplier_pct": 10},
        "MU-USD": {"unit_size": 200, "per_side_cap": 400, "max_maker_hours_per_hour": 2, "session": "US equity session", "off_session_multiplier_pct": 10},
    },
    "market_maker_fee_tiers": {
        "MM0": {"maker_hours_required": ">=250", "taker_fee_bps": 3.00, "maker_fee_rebate_bps": 0.0},
        "MM1": {"maker_hours_required": ">=360", "taker_fee_bps": 2.25, "maker_fee_rebate_bps": -0.25},
        "MM2": {"maker_hours_required": ">504", "taker_fee_bps": 2.00, "maker_fee_rebate_bps": -0.50},
    },
}

REYA_SIGNAL_PATH: dict[str, Any] = {
    "parent_slug": "reya-trading",
    "slug": "reya-signal",
    "name": "Reya RCP Signal Contribution Path",
    "verified_at": REYA_SIGNAL_VERIFIED_AT,
    "evidence_source": REYA_SIGNAL_EVIDENCE_SOURCE,
    "evidence_sources": [
        REYA_SIGNAL_EVIDENCE_SOURCE,
        REYA_SIGNAL_AMBASSADOR_SOURCE,
        REYA_SIGNAL_BLOG_INDEX_SOURCE,
    ],
    "corroboration_source": REYA_SIGNAL_CORROBORATION_SOURCE,
    "source_coverage": "PRIMARY_OFFICIAL_PLUS_INDUSTRY_CORROBORATION_NO_INDEPENDENT_EXPERT_SOURCE",
    "evidence_note": (
        "Current official Reya Chain Points FAQs still list Signal as an RCP-earning category for high-signal code, content or connections that help grow Reya, and explicitly say users can earn RCP through Signal without trading or staking. "
        "A formal official submission/review path existed through the Reya Ambassador Program: qualifying ambassador contributions were reviewed before monthly RCP allocation and the application required a wallet address. However, the Genesis Cohort application window closed on April 1, 2026. "
        "No newer currently open general Signal submission or account-linkage route was verified in Reya's current docs/blog review, so the path is blocked from execution until an official open channel is found."
    ),
    "acquisition_state": "NONFINANCIAL_REWARD_PATH_BLOCKED_NO_OPEN_CHANNEL",
    "requires_user_approval": False,
    "requires_funds": False,
    "requires_wallet_signature": False,
    "requires_real_order": False,
    "requires_asset_move": False,
    "authentication_recheck_required": True,
    "reward_deterministic": False,
    "current_submission_channel_status": "NO_CURRENT_OPEN_GENERAL_SIGNAL_SUBMISSION_CHANNEL_VERIFIED",
    "current_open_submission_verified": False,
    "known_formal_channel": "Reya Ambassador Program - Genesis Cohort",
    "known_formal_channel_status": "APPLICATION_WINDOW_CLOSED",
    "known_application_deadline": "2026-04-01",
    "terms_status": "NO_CURRENT_OPEN_SIGNAL_SUBMISSION_CHANNEL_VERIFIED_REVERIFY_FUTURE_COHORT_TERMS_ACCOUNT_LINKAGE_AND_ELIGIBILITY",
    "known_cost_or_risk": (
        "No financial action is required by the published Signal description, but reward credit is discretionary and not guaranteed. "
        "The only formal official submission/review route verified in this review was the Genesis Ambassador cohort, whose application window closed April 1, 2026 and required a wallet address. "
        "Treating an expired form or an unofficial route as current could create privacy, account-linkage, reputation or phishing risk. Spam, deceptive promotion, referral self-dealing or manufactured engagement must not be used."
    ),
    "missing_approval": (
        "No financial approval is required for Signal. The blocker is a current official open submission/recognition channel plus its account-linkage/authentication method, applicable Terms and evidence that a proposed genuine contribution is eligible for discretionary RCP consideration."
    ),
    "next_action": (
        "Monitor Reya's official RCP docs and official blog for a reopened Ambassador cohort or an explicit current Signal submission/recognition route. If one opens, verify its Terms and account linkage before preparing a genuine high-signal code or educational-content contribution. "
        "Do not submit through the expired Genesis application, auto-post, spam, manufacture engagement, use referral self-dealing, connect/sign a wallet, move assets or trade as part of this path."
    ),
    "action_taken": "NONE",
    "auto_executed": False,
    "points_delta": None,
}


def _verified_at_is_fresh(verified_at: str, *, now: datetime) -> bool:
    verified = datetime.fromisoformat(verified_at).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=OVERRIDE_TTL_DAYS)


def _is_fresh(*, now: datetime) -> bool:
    return _verified_at_is_fresh(STANDX_MAKER_VERIFIED_AT, now=now)


def _apply_reya_signal_path(result: dict[str, Any], *, now: datetime) -> bool:
    paths = result.setdefault("additional_review_paths", [])
    if not isinstance(paths, list):
        return False

    active_slugs = {str(action.get("slug")) for action in result.get("actions", [])}
    already_present = any(isinstance(path, dict) and path.get("slug") == REYA_SIGNAL_PATH["slug"] for path in paths)
    if already_present or REYA_SIGNAL_PATH["parent_slug"] not in active_slugs:
        return False
    if not _verified_at_is_fresh(REYA_SIGNAL_VERIFIED_AT, now=now):
        return False

    expires = datetime.fromisoformat(REYA_SIGNAL_VERIFIED_AT).astimezone(UTC) + timedelta(days=OVERRIDE_TTL_DAYS)
    path = copy.deepcopy(REYA_SIGNAL_PATH)
    path.update(
        {
            "evidence_status": "PRIMARY_VERIFIED_CURRENT",
            "verification_expires_at": expires.isoformat(),
        }
    )
    paths.append(path)
    if isinstance(result.get("reward_path_count"), int):
        result["reward_path_count"] += 1
    else:
        result["reward_path_count"] = len(result.get("actions", [])) + len(result.get("additional_approval_paths", [])) + len(paths)
    return True


def _refresh_review_counts(result: dict[str, Any]) -> None:
    paths = result.get("additional_review_paths", [])
    if not isinstance(paths, list):
        paths = []
    result["verified_additional_review_path_count"] = sum(
        isinstance(path, dict) and path.get("evidence_status") == "PRIMARY_VERIFIED_CURRENT" for path in paths
    )
    result["nonfinancial_review_required_count"] = sum(
        isinstance(path, dict) and path.get("acquisition_state") == "NONFINANCIAL_REWARD_PATH_REVIEW_REQUIRED" for path in paths
    )
    result["nonfinancial_blocked_no_open_channel_count"] = sum(
        isinstance(path, dict) and path.get("acquisition_state") == "NONFINANCIAL_REWARD_PATH_BLOCKED_NO_OPEN_CHANNEL" for path in paths
    )


def apply_live_overrides(report: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Refine current reward metadata only; never authorize or execute an economic or external-posting action."""
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["live_override_count"] = 0

    if _is_fresh(now=current):
        for action in result.get("actions", []):
            if action.get("slug") != "standx-maker":
                continue
            if action.get("acquisition_state") != "APPROVAL_REQUIRED_FINANCIAL":
                continue
            if not action.get("requires_user_approval"):
                continue

            expires = datetime.fromisoformat(STANDX_MAKER_VERIFIED_AT).astimezone(UTC) + timedelta(days=OVERRIDE_TTL_DAYS)
            action.update(
                {
                    "verified_at": STANDX_MAKER_VERIFIED_AT,
                    "evidence_checked_at": STANDX_MAKER_VERIFIED_AT,
                    "evidence_source": STANDX_MAKER_EVIDENCE_SOURCE,
                    "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                    "verification_expires_at": expires.isoformat(),
                    "evidence_note": (
                        "Current official StandX Community Maker Yield parameters require real executable two-sided orders within 10 bps. "
                        "Standard uptime is at least 30 minutes/hour for 0.5x and boosted uptime is at least 42 minutes/hour for 1.0x. "
                        "Proximity weight is 200% at 0 bps, 80% at 5 bps and 40% at 10 bps. Per-pair unit size, per-side caps, hourly ceilings and trading sessions are published live in America/New_York time; non-24/7 off-session hours are scored at 10%. "
                        "Yield is settled daily from a variable reward pool, so no fixed reward-per-dollar is assumed."
                    ),
                    "live_parameters": STANDX_MAKER_LIVE_PARAMETERS,
                    "terms_status": "REVERIFY_PERPS_USER_ELIGIBILITY_TERMS_AUTHENTICATION_AND_LIVE_PAIR_PARAMETERS_BEFORE_EXECUTION",
                    "known_cost_or_risk": (
                        "The qualifying quotes are real executable orders and can fill, creating directional exposure, adverse selection, spread/slippage, funding, margin and liquidation risk. "
                        "Tighter quotes receive higher proximity weight but also increase fill/adverse-selection exposure. Non-24/7 markets score only 10% outside their published session, and the daily reward pool is variable. "
                        "Per-pair unit sizes/caps and fee tiers can change, so historical or cached parameters must not be used to authorize a live plan."
                    ),
                    "missing_approval": (
                        "Current StandX Terms/jurisdiction and account eligibility, authentication/signing method, selected pair, current published unit size/per-side cap/session, current fee tier, maximum notional, allowed quote distance, intended uptime window, fee/funding/adverse-selection budget and maximum acceptable loss."
                    ),
                    "next_action": (
                        "Immediately before any economic action, re-open the live StandX Community Maker Yield page and current Terms/account eligibility, select one pair, map its current unit size/cap/session and fee tier, and calculate capped worst-case fill/funding/adverse-selection exposure. "
                        "Prepare that plan for explicit approval only; do not place, cancel, maintain or replenish real maker orders automatically."
                    ),
                    "action_taken": "NONE",
                    "auto_executed": False,
                }
            )
            result["live_override_count"] += 1
            break

    if _apply_reya_signal_path(result, now=current):
        result["live_override_count"] += 1
    _refresh_review_counts(result)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply current non-executing reward-program metadata to an Airdrop acquisition report")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    updated = apply_live_overrides(report)
    args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "live_override_count": updated.get("live_override_count", 0),
                "nonfinancial_review_required_count": updated.get("nonfinancial_review_required_count", 0),
                "nonfinancial_blocked_no_open_channel_count": updated.get("nonfinancial_blocked_no_open_channel_count", 0),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
