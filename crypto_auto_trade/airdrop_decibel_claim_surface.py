from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_CLAIM_SURFACE_VERIFIED_AT = "2026-08-17T18:44:21+00:00"
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
                "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "verification_expires_at": expires.isoformat(),
                "evidence_note": (
                    "Current official Decibel Live Campaigns says active campaigns are distributing rewards today and eligible rewards can be reviewed and claimed from the /rewards page; in-app 'Claim now' pop-ups may also surface rewards while trading. "
                    "Current Rewards Overview independently documents /rewards campaign statuses, the Claim action, a single onchain transaction that credits the trading balance, claim history and expiry windows. "
                    "These public primary pages confirm the current claim surfaces, but they do not prove that this specific account has a claimable reward before authentication."
                ),
                "claim_surface_status": "CURRENT_REWARDS_PAGE_AND_IN_APP_CLAIM_NOW_CONFIRMED",
                "terms_status": "REVERIFY_CURRENT_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_REWARD_AMOUNT_EXPIRY_AND_CLAIM_SIGNING",
                "known_cost_or_risk": (
                    "No new trade or deposit is required merely to inspect an already-earned campaign reward, but an actual claim is still a financial receipt and the official flow can involve an onchain transaction and wallet authorization. "
                    "Account-specific eligibility, reward amount, asset, expiry, transaction/signing requirements and any network cost remain unknown before authentication; reward parameters and claim windows can change, and unclaimed rewards can expire. "
                    "Receiving a USD-denominated stablecoin reward can also create recordkeeping or tax obligations depending on the user's circumstances; no tax conclusion is assumed here."
                ),
                "missing_approval": (
                    "A supported authenticated Decibel account/wallet session; current Terms/jurisdiction and exchange eligibility; an account-specific /rewards tile or in-app Claim now notification showing eligibility, reward amount, asset and expiry; confirmation of the exact transaction/signing requirements and any network cost; and explicit approval to receive the financial reward."
                ),
                "next_action": (
                    "When a supported authenticated Decibel session is available, inspect /rewards and any in-app Claim now notification for account-specific eligibility and record the status, reward amount, asset, expiry and exact signing/onchain requirements. "
                    "If a reward is Ready to Claim, keep the claim in explicit financial approval. Do not connect/sign a wallet, submit a claim transaction, trade, deposit, withdraw or move assets automatically."
                ),
                "claim_status": "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_REWARDS_PAGE_OR_IN_APP_NOTIFICATION",
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
