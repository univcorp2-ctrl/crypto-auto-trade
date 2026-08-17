from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_CLAIM_SURFACE_VERIFIED_AT = "2026-08-17T20:20:58+00:00"
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
                "evidence_status": "PRIMARY_VERIFIED_CURRENT_WITH_OFFICIAL_SOURCE_CONFLICT",
                "verification_expires_at": expires.isoformat(),
                "evidence_note": (
                    "Current official Decibel Live Campaigns says active rewards are delivered through in-app 'Claim now' pop-ups and explicitly marks the consolidated /rewards page as not yet shipped. "
                    "The current Rewards Overview likewise labels /rewards as forthcoming, while later Overview/FAQ text still describes future /rewards tiles and Claim actions. "
                    "Because the official pages are internally inconsistent, the currently verified claim-notification surface is the in-app banner/pop-up; /rewards must not be assumed live until the authenticated product UI confirms it. "
                    "These public primary pages do not prove that this specific account has a claimable reward before authentication."
                ),
                "claim_surface_status": "CURRENT_IN_APP_CLAIM_NOW_CONFIRMED_REWARDS_PAGE_NOT_YET_SHIPPED_OFFICIAL_DOC_CONFLICT",
                "terms_status": "REVERIFY_CURRENT_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_REWARD_AMOUNT_EXPIRY_AND_CLAIM_SIGNING",
                "known_cost_or_risk": (
                    "No new trade or deposit is required merely to inspect an already-earned campaign reward, but an actual claim is still a financial receipt and the official flow can involve an onchain transaction and wallet authorization. "
                    "Account-specific eligibility, reward amount, asset, expiry, transaction/signing requirements and any network cost remain unknown before authentication; reward parameters and claim windows can change, and unclaimed rewards can expire. "
                    "The official documentation currently conflicts on whether the consolidated /rewards page is deployed, so an unavailable or stale route must not be treated as evidence of account eligibility. "
                    "Receiving a USD-denominated stablecoin reward can also create recordkeeping or tax obligations depending on the user's circumstances; no tax conclusion is assumed here."
                ),
                "missing_approval": (
                    "A supported authenticated Decibel account/wallet session; current Terms/jurisdiction and exchange eligibility; an account-specific in-app unclaimed-rewards banner or 'Claim now' notification showing eligibility, reward amount, asset and expiry; confirmation of the exact transaction/signing requirements and any network cost; and explicit approval to receive the financial reward. "
                    "If the authenticated product UI exposes /rewards despite the public docs marking it not yet shipped, record that surface as additional account-specific evidence before relying on it."
                ),
                "next_action": (
                    "When a supported authenticated Decibel session is available, inspect the in-app unclaimed-rewards banner and any 'Claim now' notification first for account-specific eligibility, then record the status, reward amount, asset, expiry and exact signing/onchain requirements. "
                    "Do not assume /rewards is deployed; inspect /rewards only if the authenticated Decibel UI itself exposes that route. "
                    "If a reward is Ready to Claim, keep the actual claim in explicit financial approval. Do not connect/sign a wallet, submit a claim transaction, trade, deposit, withdraw or move assets automatically."
                ),
                "claim_status": "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_IN_APP_CLAIM_NOTIFICATION",
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
