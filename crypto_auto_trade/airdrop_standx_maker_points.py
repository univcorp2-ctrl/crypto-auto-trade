from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

STANDX_MAKER_POINTS_VERIFIED_AT = "2026-08-17T11:20:00+00:00"
STANDX_NETWORK_YIELD_SOURCE = "https://docs.standx.com/docs/standx-perps-solutions/network-yield"
STANDX_MAINNET_SOURCE = "https://docs.standx.com/blog/articles/standx-mainnet-now-live-trade-for-real"
STANDX_MAKER_POINTS_FIELD_NOTES_SOURCE = (
    "https://docs.standx.com/blog/articles/orderbook-alo-maker-points-a-traders-field-notes-on-standx"
)
STANDX_MAKER_POINTS_EXPERIENCE_SOURCE = (
    "https://docs.standx.com/blog/articles/my-standx-maker-points-bot-experience-and-maker-uptime-results"
)

STANDX_MAKER_POINTS_PATH: dict[str, Any] = {
    "parent_slug": "standx-maker",
    "slug": "standx-maker-points",
    "name": "StandX Maker Points Passive-Liquidity Path",
    "verified_at": STANDX_MAKER_POINTS_VERIFIED_AT,
    "evidence_source": STANDX_NETWORK_YIELD_SOURCE,
    "evidence_sources": [
        STANDX_NETWORK_YIELD_SOURCE,
        STANDX_MAINNET_SOURCE,
        STANDX_MAKER_POINTS_FIELD_NOTES_SOURCE,
        STANDX_MAKER_POINTS_EXPERIENCE_SOURCE,
    ],
    "source_coverage": "CURRENT_OFFICIAL_PROGRAM_REFERENCE_PLUS_STANDX_HOSTED_COMMUNITY_OPERATIONAL_CORROBORATION_NO_INDEPENDENT_EXPERT_SOURCE",
    "evidence_note": (
        "Current official StandX Network Yield documentation explicitly identifies Maker Points as points earned from market-making activity, alongside Trader and Holder Points, and the official Mainnet launch confirms that Mainnet points operate with real-money Perps activity. "
        "StandX-hosted community field notes describe Maker Points accruing from passive limit orders based on order value, duration and distance from market, including orders that remain unfilled; a separate StandX-hosted community execution report shows that such orders can in fact fill and create fees and realized loss. "
        "Because the exact current Maker Points scoring table was not found in a current primary StandX rules page during this review, the action class is considered supported but the detailed scoring formula remains a pre-execution recheck rather than a guaranteed reward-per-dollar formula."
    ),
    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
    "requires_user_approval": True,
    "requires_funds": True,
    "requires_wallet_signature": True,
    "wallet_signature_requirement": "FAIL_CLOSED_UNTIL_CURRENT_ACCOUNT_AND_ORDER_AUTHENTICATION_FLOW_IS_VERIFIED",
    "requires_real_order": True,
    "requires_asset_move": False,
    "authentication_recheck_required": True,
    "terms_status": "REVERIFY_CURRENT_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_MAKER_POINTS_SCORING_AND_ORDER_AUTHENTICATION",
    "known_cost_or_risk": (
        "Maker Points are not a zero-risk click: the qualifying activity uses real limit orders on a live perpetual order book. A resting order can be filled and create directional exposure, fees, funding, margin and liquidation risk. "
        "Add-Liquidity-Only/post-only behavior can reduce accidental taker execution but does not prevent a resting maker order from later being filled. StandX-hosted community evidence documents actual fills, fees and realized losses while farming Maker Points. "
        "The current point value and exact current scoring formula are not independently verified, so no profitability, cash-value or reward-per-dollar assumption is made."
    ),
    "missing_approval": (
        "Current StandX Terms/jurisdiction and account eligibility; authenticated Perps/points surface; current Maker Points scoring and eligible markets; current order authentication/signing method and ALO/post-only behavior; available existing collateral; selected pair; maximum order notional; allowed distance and duration; maximum simultaneous fill exposure; cancellation/renewal rules; fee/funding budget; and maximum acceptable loss. "
        "Any deposit, wallet transfer or collateral move needed to fund the Perps account requires separate explicit asset-movement approval."
    ),
    "next_action": (
        "In a supported authenticated StandX session, perform a read-only check of the current Points/Maker Points page, eligible markets and order-authentication/ALO controls. If the current Maker Points rules still reward passive market-making orders, prepare a tightly capped post-only/ALO plan for explicit financial approval with maximum notional, fill exposure and loss budget. "
        "Do not place, cancel or renew any real order, move collateral, connect/sign a wallet, manufacture volume, self-trade or quote-stuff automatically."
    ),
    "prohibited_methods": [
        "self_trading",
        "wash_trading",
        "manufactured_volume",
        "quote_stuffing",
        "spoofing_or_non_bona_fide_orders",
        "anti_bot_or_region_evasion",
    ],
    "action_taken": "NONE",
    "auto_executed": False,
    "points_delta": None,
}


def _verified_at_is_fresh(verified_at: str, *, now: datetime) -> bool:
    verified = datetime.fromisoformat(verified_at).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=VERIFICATION_TTL_DAYS)


def apply_standx_maker_points_path(report: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Append the current StandX Maker Points path as approval-only; never place orders."""
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    paths = result.setdefault("additional_approval_paths", [])
    if not isinstance(paths, list):
        return result

    active_slugs = {str(action.get("slug")) for action in result.get("actions", []) if isinstance(action, dict)}
    already_present = any(isinstance(path, dict) and path.get("slug") == STANDX_MAKER_POINTS_PATH["slug"] for path in paths)
    if already_present or STANDX_MAKER_POINTS_PATH["parent_slug"] not in active_slugs:
        return result
    if not _verified_at_is_fresh(STANDX_MAKER_POINTS_VERIFIED_AT, now=current):
        return result

    expires = datetime.fromisoformat(STANDX_MAKER_POINTS_VERIFIED_AT).astimezone(UTC) + timedelta(days=VERIFICATION_TTL_DAYS)
    path = copy.deepcopy(STANDX_MAKER_POINTS_PATH)
    path.update(
        {
            "evidence_status": "PRIMARY_VERIFIED_CURRENT_ACTION_CLASS_SCORING_RECHECK_REQUIRED",
            "verification_expires_at": expires.isoformat(),
        }
    )
    paths.append(path)
    result["reward_path_count"] = int(result.get("reward_path_count", len(result.get("actions", [])))) + 1
    result["verified_additional_path_count"] = int(result.get("verified_additional_path_count", 0)) + 1
    result["additional_approval_required_count"] = int(result.get("additional_approval_required_count", 0)) + 1
    result["approval_required_count"] = int(result.get("approval_required_count", 0)) + 1
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply current StandX Maker Points approval-only reward path")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    result = apply_standx_maker_points_path(report)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "reward_path_count": result.get("reward_path_count"),
                "verified_additional_path_count": result.get("verified_additional_path_count"),
                "additional_approval_required_count": result.get("additional_approval_required_count"),
                "approval_required_count": result.get("approval_required_count"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
