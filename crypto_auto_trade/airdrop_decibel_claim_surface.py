from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_CLAIM_SURFACE_VERIFIED_AT = "2026-08-18T09:25:45+00:00"
DECIBEL_LIVE_CAMPAIGNS_SOURCE = "https://docs.decibel.trade/rewards/campaigns/live"
DECIBEL_REWARDS_OVERVIEW_SOURCE = "https://docs.decibel.trade/rewards/overview"
DECIBEL_REWARDS_FAQ_SOURCE = "https://docs.decibel.trade/rewards/faq"
DECIBEL_REWARDS_APP_SOURCE = "https://app.decibel.trade/rewards"


def _is_fresh(*, now: datetime) -> bool:
    verified = datetime.fromisoformat(DECIBEL_CLAIM_SURFACE_VERIFIED_AT).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=VERIFICATION_TTL_DAYS)


def apply_decibel_claim_surface(report: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Refresh the current Decibel claim surface without executing any claim or wallet action."""
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["decibel_claim_surface_override_count"] = 0

    if not _is_fresh(now=current):
        return result

    paths = result.get("additional_approval_paths", [])
    if not isinstance(paths, list):
        return result

    for path in paths:
        if not isinstance(path, dict) or path.get("slug") != "decibel-campaign-claims":
            continue
        if path.get("acquisition_state") != "APPROVAL_REQUIRED_FINANCIAL":
            continue

        expires = datetime.fromisoformat(DECIBEL_CLAIM_SURFACE_VERIFIED_AT).astimezone(UTC) + timedelta(days=VERIFICATION_TTL_DAYS)
        path.update(
            {
                "verified_at": DECIBEL_CLAIM_SURFACE_VERIFIED_AT,
                "evidence_checked_at": DECIBEL_CLAIM_SURFACE_VERIFIED_AT,
                "evidence_source": DECIBEL_LIVE_CAMPAIGNS_SOURCE,
                "evidence_sources": [
                    DECIBEL_LIVE_CAMPAIGNS_SOURCE,
                    DECIBEL_REWARDS_OVERVIEW_SOURCE,
                    DECIBEL_REWARDS_FAQ_SOURCE,
                    DECIBEL_REWARDS_APP_SOURCE,
                    "https://decibel.trade/terms-of-service",
                ],
                "evidence_status": "PRIMARY_VERIFIED_CURRENT_CONFLICT_FAIL_CLOSED",
                "verification_expires_at": expires.isoformat(),
                "evidence_note": (
                    "Current official Decibel Live Campaigns says the listed campaigns are active and distributing rewards today, but explicitly says the /rewards page is coming soon and that active rewards are currently delivered via in-app 'Claim now' pop-ups. "
                    "The current Rewards Overview independently labels /rewards as coming soon while also describing the future /rewards review/claim flow, and the FAQ still refers to /rewards tiles. "
                    "Because the official pages mix current and future claim-surface language, the agent fails closed: the current public claim surface is treated as the authenticated in-app 'Claim now' notification only, and /rewards is not treated as a current acquisition route until Decibel's current-state documentation or an authenticated account surface confirms that it has shipped. "
                    "The existence of a public /rewards route does not override the current Live Campaigns statement or prove account-specific eligibility."
                ),
                "claim_surface_status": "CURRENT_IN_APP_CLAIM_NOW_CONFIRMED_REWARDS_PAGE_COMING_SOON_UNCONFIRMED",
                "terms_status": "CURRENT_PUBLIC_TERMS_REVIEWED_REVERIFY_ACCOUNT_JURISDICTION_ELIGIBILITY_REWARD_AMOUNT_EXPIRY_AND_CLAIM_SIGNING",
                "known_cost_or_risk": (
                    "No new trade or deposit is required merely to inspect an already-earned campaign notification, but an actual campaign claim is a financial receipt. Current Decibel documentation says campaign rewards are credited to the trading account and describes an onchain claim flow, while the exact current account-specific signing/transaction path remains unknown until authenticated inspection. "
                    "Account-specific eligibility, reward amount, asset, expiry, exact transaction/signing requirements and any network cost remain unknown before authenticated inspection; reward parameters and claim windows can change, and unclaimed rewards can expire. "
                    "Decibel's current Terms state that supplemental terms may apply and that users are responsible for jurisdictional compliance. Receiving a USD-denominated stablecoin reward can also create recordkeeping or tax obligations depending on the user's circumstances; no tax conclusion is assumed here."
                ),
                "missing_approval": (
                    "A supported already-authenticated Decibel session for read-only inspection of the current in-app unclaimed-reward banner/'Claim now' notification; confirmation that the account is eligible under current Terms/jurisdiction; an account-specific claimable reward showing amount, asset and expiry; confirmation of the exact transaction/signing requirements and any network cost; and explicit approval to receive the financial reward."
                ),
                "next_action": (
                    "In a supported already-authenticated Decibel session, inspect the current in-app unclaimed-rewards banner/'Claim now' notification for account-specific eligibility, claimable status, reward amount, asset, expiry and exact signing/onchain requirements. "
                    "Do not use /rewards as the current claim route unless Decibel's current-state documentation or the authenticated account surface confirms it is live. If a reward is claimable, record those details and keep the actual claim in explicit financial approval. Do not connect/sign a wallet, submit a claim transaction, trade, deposit, withdraw or move assets automatically."
                ),
                "claim_status": "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_IN_APP_CLAIM_NOW_NOTIFICATION",
                "action_taken": "NONE",
                "auto_executed": False,
                "points_delta": None,
            }
        )
        result["decibel_claim_surface_override_count"] = 1
        break

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh current Decibel campaign claim-surface metadata without executing claims")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    updated = apply_decibel_claim_surface(report)
    args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decibel_claim_surface_override_count": updated.get("decibel_claim_surface_override_count", 0)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
