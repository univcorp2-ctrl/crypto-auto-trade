from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_CLAIM_SURFACE_VERIFIED_AT = "2026-08-17T18:24:18+00:00"
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
                "evidence_status": "PRIMARY_VERIFIED_CURRENT_WITH_OFFICIAL_TIME_AXIS_CONFLICT",
                "verification_expires_at": expires.isoformat(),
                "evidence_note": (
                    "Current top-level official Decibel Live Campaigns guidance says the /rewards page is coming soon and that active rewards are currently delivered via in-app 'Claim now' pop-ups. "
                    "Rewards Overview likewise labels /rewards as coming soon/upcoming while describing its future statuses and claim flow. Lower campaign instructions and the FAQ still refer to visiting /rewards, creating an official current/future time-axis conflict. "
                    "Fail closed on the current surface: treat in-app Claim now as the presently verified delivery route and do not treat /rewards as live until an authenticated account actually exposes it or Decibel's top-level current guidance changes. Public docs still do not prove that this specific account has a claimable reward."
                ),
                "claim_surface_status": "CURRENT_IN_APP_CLAIM_NOW_CONFIRMED_REWARDS_PAGE_COMING_SOON_OR_TIME_AXIS_CONFLICT",
                "terms_status": "REVERIFY_CURRENT_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_REWARD_AMOUNT_EXPIRY_CLAIM_SIGNING_AND_REWARDS_PAGE_LIVE_STATUS",
                "known_cost_or_risk": (
                    "No new trade or deposit is required merely to inspect an already-earned campaign reward, but an actual claim is still a financial receipt and the official flow can involve an onchain transaction and wallet authorization. "
                    "Account-specific eligibility, reward amount, asset, expiry, transaction/signing requirements and any network cost remain unknown before authentication; reward parameters and claim windows can change, and unclaimed rewards can expire. "
                    "The official public pages currently mix present-tense in-app delivery with future /rewards instructions, so assuming the web rewards page is live could send the agent to a nonexistent or stale surface. Receiving a USD-denominated stablecoin reward can also create recordkeeping or tax obligations depending on the user's circumstances; no tax conclusion is assumed here."
                ),
                "missing_approval": (
                    "A supported authenticated Decibel account/wallet session; current Terms/jurisdiction and exchange eligibility; an account-specific in-app Claim now notification showing eligibility, reward amount, asset and expiry; confirmation of the exact transaction/signing requirements and any network cost; and explicit approval to receive the financial reward. If an authenticated /rewards page is actually live for the account, record that observation separately before using it as a current surface."
                ),
                "next_action": (
                    "When a supported authenticated Decibel session is available, inspect the in-app Claim now notification first and record account-specific eligibility, reward amount, asset, expiry and exact signing/onchain requirements. If the authenticated account also exposes a live /rewards page, record that as a separate current observation rather than assuming it from public future-facing docs. "
                    "If a reward is claimable, keep the claim in explicit financial approval. Do not connect/sign a wallet, submit a claim transaction, trade, deposit, withdraw or move assets automatically."
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
