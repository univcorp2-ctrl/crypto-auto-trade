from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

STANDX_NETWORK_YIELD_VERIFIED_AT = "2026-08-15T17:20:00+00:00"
STANDX_NETWORK_YIELD_SOURCE = "https://docs.standx.com/docs/standx-perps-solutions/network-yield"

STANDX_NETWORK_YIELD_PATH: dict[str, Any] = {
    "parent_slug": "standx-maker",
    "slug": "standx-network-yield",
    "name": "StandX Network Yield Referral / Points Path",
    "verified_at": STANDX_NETWORK_YIELD_VERIFIED_AT,
    "evidence_source": STANDX_NETWORK_YIELD_SOURCE,
    "evidence_sources": [STANDX_NETWORK_YIELD_SOURCE],
    "evidence_note": (
        "Current official StandX Network Yield documentation says the referral-based rewards program shares up to 20% of invitees' trading fees. "
        "Network Yield is not active by default: the 5% base rate unlocks after 500,000 DUSD of cumulative personal trading volume, with all historical personal volume counting. "
        "Higher 10% / 15% / 20% tiers currently require 2.5m / 7.5m / 15m DUSD of post-launch Network Volume, and StandX says those rates and thresholds may change. "
        "The same page also says both referrer and invitee receive a +5% bonus on points earned from trading activity across Trader, Maker and Holder Points."
    ),
    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
    "requires_user_approval": True,
    "requires_funds": True,
    "requires_wallet_signature": False,
    "requires_real_order": True,
    "requires_asset_move": False,
    "authentication_recheck_required": True,
    "terms_status": "REVERIFY_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_NETWORK_ACTIVATION_AND_REFERRAL_RULES",
    "known_cost_or_risk": (
        "If the account has not already accumulated 500,000 DUSD of personal trading volume, activating the base Network Yield rate would require additional genuine trading and therefore fees, spread/slippage, funding, margin/liquidation and directional PnL risk. "
        "Higher tiers depend on genuine network trading volume, and the published thresholds/rates can change. Referral rewards must come from genuine third-party activity: self-referral, referral self-dealing, wash trading, manufactured volume, spam or deceptive promotion are prohibited by this agent. "
        "The points bonus does not establish a verified cash value for points, so no reward-per-dollar or profitability assumption is made."
    ),
    "missing_approval": (
        "Current StandX Terms/jurisdiction and account eligibility/authentication; whether the account already satisfies the 500,000 DUSD historical personal-volume activation threshold; the current Network Yield table/share-rate configuration; and, only if an activation volume gap exists, explicit maximum additional notional, fee/spread/funding budget, leverage and maximum acceptable loss. "
        "Any referral activity must involve genuine independent third parties and must not use self-referral, spam, misleading claims or manufactured trading."
    ),
    "next_action": (
        "Re-open the current Network Yield page and authenticated Network dashboard, verify Terms/account eligibility and whether the 5% base rate is already unlockable from historical volume. "
        "If already eligible, prepare only the non-financial activation/share-rate setting for review; if a trading-volume gap remains, calculate a capped genuine-trading plan and keep it in explicit financial approval. "
        "Do not place orders, move assets, connect/sign a wallet, self-refer, spam invitees or manufacture network volume automatically."
    ),
    "action_taken": "NONE",
    "auto_executed": False,
    "points_delta": None,
}

DECIBEL_CAMPAIGN_CLAIM_VERIFIED_AT = "2026-08-16T04:34:05+00:00"
DECIBEL_CAMPAIGN_OVERVIEW_SOURCE = "https://docs.decibel.trade/rewards/overview"
DECIBEL_CAMPAIGN_FAQ_SOURCE = "https://docs.decibel.trade/rewards/faq"
DECIBEL_CAMPAIGN_LIVE_SOURCE = "https://docs.decibel.trade/rewards/campaigns/live"

DECIBEL_CAMPAIGN_CLAIM_PATH: dict[str, Any] = {
    "parent_slug": "decibel-trading",
    "slug": "decibel-campaign-claims",
    "name": "Decibel Campaign Stablecoin Claim Path",
    "verified_at": DECIBEL_CAMPAIGN_CLAIM_VERIFIED_AT,
    "evidence_source": DECIBEL_CAMPAIGN_LIVE_SOURCE,
    "evidence_sources": [
        DECIBEL_CAMPAIGN_LIVE_SOURCE,
        DECIBEL_CAMPAIGN_OVERVIEW_SOURCE,
        DECIBEL_CAMPAIGN_FAQ_SOURCE,
        "https://app.decibel.trade/trade",
    ],
    "evidence_note": (
        "Current official Decibel Rewards documentation says Campaigns are separate from Amps and pay USD-denominated stablecoin rewards for specific activities. "
        "The current Live Campaigns page says the /rewards page is still coming soon and that active account-specific rewards are currently delivered through in-app 'Claim now' pop-ups. "
        "The overview describes the future /rewards statuses such as Ready to Claim, while the current claim flow remains the in-app notification. A successful campaign claim credits the trading-account balance in a single onchain transaction, and recurring unclaimed rewards can expire. "
        "Most campaigns are automatically evaluated, while some require advance opt-in. The public Decibel app requires wallet/account authentication before account-specific claim availability can be inspected."
    ),
    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
    "requires_user_approval": True,
    "requires_funds": False,
    "requires_wallet_signature": True,
    "requires_real_order": False,
    "requires_asset_move": True,
    "authentication_recheck_required": True,
    "terms_status": "REVERIFY_CURRENT_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_IN_APP_CLAIM_AMOUNT_EXPIRY_AND_CLAIM_SIGNING",
    "known_cost_or_risk": (
        "The claim itself does not require a new trade or deposit according to the public reward flow, but it is a financial receipt: a USD-denominated stablecoin reward is credited onchain to the trading account. "
        "Account-specific eligibility, amount and expiry are unavailable before authentication, claim pools can be exhausted, reward parameters can change, and the exact wallet-signing/onchain transaction flow must be rechecked immediately before any claim. "
        "The documented /rewards page is not yet the current delivery surface, so automation must not navigate to or rely on a future page as though it were live. Receiving a financial reward can also create recordkeeping or tax obligations depending on the user's circumstances; no tax conclusion is assumed here."
    ),
    "missing_approval": (
        "A supported authenticated Decibel account/wallet session; current Terms/jurisdiction and exchange eligibility; an actual account-specific in-app 'Claim now' pop-up or equivalent current claim notification showing the reward amount, asset and expiry; confirmation of the claim transaction/signing mechanics and any network cost; and explicit approval to receive the financial reward."
    ),
    "next_action": (
        "When a supported authenticated Decibel session is available, inspect only the current account-specific in-app 'Claim now' pop-up or equivalent reward notification. If a claim is offered, record the reward amount, asset, expiry and exact signing/onchain requirements, then keep the claim in explicit financial approval. "
        "Do not connect/sign a wallet, claim a stablecoin reward, trade, deposit, withdraw or move assets automatically. Do not treat the future /rewards page as a live acquisition route until Decibel officially ships it."
    ),
    "claim_status": "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_IN_APP_CLAIM_NOTIFICATION",
    "action_taken": "NONE",
    "auto_executed": False,
    "points_delta": None,
}


def _verified_at_is_fresh(verified_at: str, *, now: datetime) -> bool:
    verified = datetime.fromisoformat(verified_at).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=VERIFICATION_TTL_DAYS)


def _is_fresh(*, now: datetime) -> bool:
    return _verified_at_is_fresh(STANDX_NETWORK_YIELD_VERIFIED_AT, now=now)


def _append_path_if_current(
    result: dict[str, Any],
    *,
    path_spec: dict[str, Any],
    now: datetime,
) -> None:
    paths = result.setdefault("additional_approval_paths", [])
    if not isinstance(paths, list):
        return

    active_slugs = {str(action.get("slug")) for action in result.get("actions", []) if isinstance(action, dict)}
    path_slug = str(path_spec["slug"])
    already_present = any(isinstance(path, dict) and path.get("slug") == path_slug for path in paths)
    verified_at = str(path_spec["verified_at"])
    if already_present or str(path_spec["parent_slug"]) not in active_slugs or not _verified_at_is_fresh(verified_at, now=now):
        return

    expires = datetime.fromisoformat(verified_at).astimezone(UTC) + timedelta(days=VERIFICATION_TTL_DAYS)
    path = copy.deepcopy(path_spec)
    path.update(
        {
            "evidence_status": "PRIMARY_VERIFIED_CURRENT",
            "verification_expires_at": expires.isoformat(),
        }
    )
    paths.append(path)

    result["reward_path_count"] = int(result.get("reward_path_count", len(result.get("actions", [])))) + 1
    result["verified_additional_path_count"] = int(result.get("verified_additional_path_count", 0)) + 1
    result["additional_approval_required_count"] = int(result.get("additional_approval_required_count", 0)) + 1
    result["approval_required_count"] = int(result.get("approval_required_count", 0)) + 1


def apply_additional_current_paths(report: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Append newly verified approval-only reward paths without authorizing execution."""
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)

    _append_path_if_current(result, path_spec=STANDX_NETWORK_YIELD_PATH, now=current)
    _append_path_if_current(result, path_spec=DECIBEL_CAMPAIGN_CLAIM_PATH, now=current)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply current additional approval-only Airdrop reward paths")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    result = apply_additional_current_paths(report)
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
