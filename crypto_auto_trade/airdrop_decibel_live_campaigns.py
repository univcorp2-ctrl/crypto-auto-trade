from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_LIVE_CAMPAIGNS_VERIFIED_AT = "2026-08-15T22:23:38+00:00"
DECIBEL_LIVE_CAMPAIGNS_SOURCE = "https://docs.decibel.trade/rewards/campaigns/live"
DECIBEL_TERMS_SOURCE = "https://decibel.trade/terms-of-service"

DECIBEL_FIRST_TRADE_ON_US_PATH: dict[str, Any] = {
    "parent_slug": "decibel-trading",
    "slug": "decibel-first-trade-on-us",
    "name": "Decibel First Trade on Us Campaign",
    "verified_at": DECIBEL_LIVE_CAMPAIGNS_VERIFIED_AT,
    "evidence_source": DECIBEL_LIVE_CAMPAIGNS_SOURCE,
    "evidence_sources": [DECIBEL_LIVE_CAMPAIGNS_SOURCE, DECIBEL_TERMS_SOURCE],
    "evidence_note": (
        "The current official Decibel Live Campaigns page lists First Trade on Us as running July 21 through October 21, 2026. "
        "It requires an eligible trader who has not previously claimed the credit to deposit 250-5,000 USDC, choose 20x/30x/40x leverage, and redeem one sponsored two-minute BTC position. "
        "The selected leverage locks withdrawals for 1/4/7 days respectively; if the sponsored position loses, the campaign says nothing is deducted from the deposit, while profit is credited to the Decibel account. "
        "The page limits the trial to one per wallet and says additional eligibility conditions and campaign-specific rules apply."
    ),
    "campaign_duration": "2026-07-21_TO_2026-10-21",
    "deposit_usdc_min": 250,
    "deposit_usdc_max": 5000,
    "leverage_to_lock_days": {"20x": 1, "30x": 4, "40x": 7},
    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
    "requires_user_approval": True,
    "requires_funds": True,
    "requires_wallet_signature": True,
    "requires_real_order": True,
    "requires_asset_move": True,
    "authentication_recheck_required": True,
    "terms_status": "REVERIFY_ACCOUNT_ELIGIBILITY_CURRENT_TERMS_CAMPAIGN_RULES_WALLET_DEPOSIT_LOCK_AND_SPONSORED_POSITION_FLOW",
    "known_cost_or_risk": (
        "This is not a zero-value-transfer action: it requires depositing 250-5,000 USDC and accepting a 1/4/7-day withdrawal lock. "
        "Redeeming the credit opens a real two-minute BTC position even though Decibel states campaign losses are sponsored. The deposit remains exposed to platform/protocol, wallet, smart-contract, stablecoin, availability and withdrawal risks, and any separate user-initiated trades are not covered. "
        "The Terms make campaigns discretionary and subject to supplemental campaign rules; the linked campaign-specific rules could not be independently retrieved in this review, so full campaign-specific legal terms remain unverified."
    ),
    "missing_approval": (
        "A supported authenticated Decibel account/wallet session; confirmation that the account has not previously claimed the campaign and is eligible under current Terms and campaign-specific rules; the exact deposit amount, selected leverage/lock period, network/wallet transaction requirements and current campaign availability; and explicit approval to deposit/lock funds and redeem the sponsored real position."
    ),
    "next_action": (
        "In an authenticated Decibel session, inspect only the First Trade on Us reward tile and current campaign rules, account eligibility, deposit network and lock terms. Record the exact eligible amount and transaction/signing requirements, then keep the action in explicit financial approval. "
        "Do not connect/sign a wallet, deposit USDC, lock funds or redeem/open the sponsored position automatically."
    ),
    "action_taken": "NONE",
    "auto_executed": False,
    "points_delta": None,
}

DECIBEL_MAKER_REBATE_PATH: dict[str, Any] = {
    "parent_slug": "decibel-trading",
    "slug": "decibel-maker-rebate",
    "name": "Decibel Maker Rebate Campaign",
    "verified_at": DECIBEL_LIVE_CAMPAIGNS_VERIFIED_AT,
    "evidence_source": DECIBEL_LIVE_CAMPAIGNS_SOURCE,
    "evidence_sources": [DECIBEL_LIVE_CAMPAIGNS_SOURCE, DECIBEL_TERMS_SOURCE],
    "evidence_note": (
        "The current directly opened Decibel Live Campaigns page says Maker Rebate is live and pays 0.5 bps on maker fill volume from bulk/batch orders. "
        "Eligibility requires at least an 80% maker ratio for the weekly period; standard single-order fills are excluded. The current page lists a 25,000 USD monthly cap, possible pro-rata payouts if qualified rebates exceed the cap, on-chain allocation/claim, and month-end expiration for unclaimed weekly rebates. "
        "A search-index snapshot of the same official page returned an older 0.25 bps value, so the direct current page is used for this snapshot and the rebate rate must be re-opened immediately before any financial plan."
    ),
    "maker_rebate_bps_direct_current": 0.5,
    "minimum_maker_ratio_pct": 80,
    "qualifying_order_type": "BULK_BATCH_MAKER_FILLS_ONLY",
    "monthly_cap_usd": 25000,
    "source_conflict": "SEARCH_INDEX_SNAPSHOT_0_25_BPS_VS_DIRECT_CURRENT_PAGE_0_5_BPS",
    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
    "requires_user_approval": True,
    "requires_funds": True,
    "requires_wallet_signature": True,
    "requires_real_order": True,
    "requires_asset_move": False,
    "authentication_recheck_required": True,
    "terms_status": "REVERIFY_CURRENT_DIRECT_REBATE_RATE_TERMS_ACCOUNT_ELIGIBILITY_BULK_ORDER_AUTHENTICATION_MAKER_RATIO_AND_CLAIM_FLOW",
    "known_cost_or_risk": (
        "Qualifying requires genuine maker fills from bulk/batch orders. Real orders can fill and create inventory/directional exposure, adverse selection, fees, spread, funding, margin and liquidation risk. "
        "The 0.5 bps rebate shown on the current direct page is small relative to potential trading losses and may be prorated; it must not be treated as proof of positive expected value. "
        "The conflicting older 0.25 bps search snapshot shows that campaign parameters can drift, and any eventual claim is an on-chain financial receipt requiring current authentication/signing review."
    ),
    "missing_approval": (
        "Current direct campaign rate and cap recheck; current Terms/account eligibility; authenticated bulk-order capability and current maker ratio; explicit markets, maximum notional/inventory, quoting parameters, leverage, fee/funding budget, maximum acceptable loss and claim-signing requirements."
    ),
    "next_action": (
        "Re-open the direct Live Campaigns page and authenticated Decibel account immediately before planning, verify the current rebate rate, maker ratio, bulk-order eligibility and claim mechanics, then prepare only a capped genuine maker plan for explicit approval. "
        "Do not place bulk or standard orders, manufacture maker volume, self-trade, wash trade, sign a claim or move assets automatically."
    ),
    "action_taken": "NONE",
    "auto_executed": False,
    "points_delta": None,
}

DECIBEL_CAMPAIGN_EXCLUSIONS: list[dict[str, str]] = [
    {
        "slug": "decibel-global-warming-home-cooling",
        "state": "EXCLUDED_DATE_CONFLICT",
        "reason": (
            "The current Live Campaigns page labels this campaign live, but the same page states a fixed July 7-July 28, 2026 duration. Because July 28 is already past, the agent does not treat the live label as sufficient evidence of current eligibility."
        ),
    },
    {
        "slug": "decibel-liquidation-rebate-qualification",
        "state": "EXCLUDED_HARMFUL_QUALIFICATION",
        "reason": (
            "The current campaign requires a prior liquidation plus redeposit and a new trade. The agent will never seek or induce liquidation to qualify; an already-earned Ready to Claim rebate may only be handled by the existing approval-gated generic campaign claim path."
        ),
    },
]


def _is_fresh(verified_at: str, *, now: datetime) -> bool:
    verified = datetime.fromisoformat(verified_at).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=VERIFICATION_TTL_DAYS)


def _append_path(result: dict[str, Any], *, path_spec: dict[str, Any], now: datetime) -> None:
    paths = result.setdefault("additional_approval_paths", [])
    if not isinstance(paths, list):
        return
    active_slugs = {str(action.get("slug")) for action in result.get("actions", []) if isinstance(action, dict)}
    if str(path_spec["parent_slug"]) not in active_slugs:
        return
    if any(isinstance(path, dict) and path.get("slug") == path_spec["slug"] for path in paths):
        return
    verified_at = str(path_spec["verified_at"])
    if not _is_fresh(verified_at, now=now):
        return

    expires = datetime.fromisoformat(verified_at).astimezone(UTC) + timedelta(days=VERIFICATION_TTL_DAYS)
    path = copy.deepcopy(path_spec)
    path.update({"evidence_status": "PRIMARY_VERIFIED_CURRENT", "verification_expires_at": expires.isoformat()})
    paths.append(path)
    result["reward_path_count"] = int(result.get("reward_path_count", len(result.get("actions", [])))) + 1
    result["verified_additional_path_count"] = int(result.get("verified_additional_path_count", 0)) + 1
    result["additional_approval_required_count"] = int(result.get("additional_approval_required_count", 0)) + 1
    result["approval_required_count"] = int(result.get("approval_required_count", 0)) + 1


def _merge_exclusions(result: dict[str, Any]) -> None:
    exclusions = result.setdefault("campaign_exclusions", [])
    if not isinstance(exclusions, list):
        return
    existing = {str(item.get("slug")) for item in exclusions if isinstance(item, dict)}
    for exclusion in DECIBEL_CAMPAIGN_EXCLUSIONS:
        if exclusion["slug"] not in existing:
            exclusions.append(copy.deepcopy(exclusion))


def apply_decibel_live_campaigns(report: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    _append_path(result, path_spec=DECIBEL_FIRST_TRADE_ON_US_PATH, now=current)
    _append_path(result, path_spec=DECIBEL_MAKER_REBATE_PATH, now=current)
    _merge_exclusions(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply current Decibel live campaign approval-only paths")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    result = apply_decibel_live_campaigns(report)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "reward_path_count": result.get("reward_path_count"),
        "additional_approval_required_count": result.get("additional_approval_required_count"),
        "approval_required_count": result.get("approval_required_count"),
        "campaign_exclusion_count": len(result.get("campaign_exclusions", [])),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
