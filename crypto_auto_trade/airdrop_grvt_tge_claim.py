from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

GRVT_TGE_CLAIM_VERIFIED_AT = "2026-08-18T01:22:00+00:00"
GRVT_TGE_OVERVIEW_SOURCE = "https://help.grvt.io/en/articles/16106859-everything-about-tge"
GRVT_TGE_CLAIM_SOURCE = "https://help.grvt.io/en/articles/16143304-how-to-receive-and-manage-your-grvt-airdrop"
GRVT_RESTRICTED_JURISDICTIONS_SOURCE = "https://help.grvt.io/en/articles/9711621-restricted-jurisdictions"
GRVT_REWARD_PORTAL = "https://grvt.io/exchange/reward-portal"

GRVT_TGE_CLAIM_PATH: dict[str, Any] = {
    "parent_slug": "grvt",
    "slug": "grvt-tge-tranche-claim",
    "name": "GRVT TGE Released-Tranche Claim Path",
    "verified_at": GRVT_TGE_CLAIM_VERIFIED_AT,
    "evidence_source": GRVT_TGE_CLAIM_SOURCE,
    "evidence_sources": [
        GRVT_TGE_CLAIM_SOURCE,
        GRVT_TGE_OVERVIEW_SOURCE,
        GRVT_RESTRICTED_JURISDICTIONS_SOURCE,
        GRVT_REWARD_PORTAL,
    ],
    "evidence_note": (
        "Current official GRVT TGE documentation says eligible $GRVT allocations are released in tranches and that, after the first tranche, released tranches generally require the user to claim them in the app within 30 days or they expire. "
        "The current official receive/manage guide says a manually claimable batch is claimed by logging in to the GRVT account, opening the Reward Portal, locating the claimable batch and clicking Claim, after which $GRVT is credited to the GRVT account. "
        "No deposit, bridge, real order or token approval is described as a prerequisite for the manual claim itself. However, the claim is a financial receipt of $GRVT and therefore remains explicit-approval-only. "
        "Two current official TGE help articles conflict on the registration deadline (27 July 2026 versus 6 August 2026), so account-specific registration/eligibility must be treated as unknown until the authenticated Reward Portal is inspected."
    ),
    "source_conflict": "OFFICIAL_TGE_ARTICLES_DISAGREE_ON_REGISTRATION_DEADLINE_2026_07_27_VS_2026_08_06",
    "claim_window_days": 30,
    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
    "requires_user_approval": True,
    "requires_funds": False,
    "requires_wallet_signature": False,
    "wallet_signature_requirement": "NOT_STATED_IN_CURRENT_PUBLIC_CLAIM_INSTRUCTIONS_REVERIFY_AUTHENTICATED_FLOW",
    "requires_real_order": False,
    "requires_asset_move": True,
    "authentication_recheck_required": True,
    "terms_status": "REVERIFY_ACCOUNT_REGISTRATION_ELIGIBILITY_CURRENT_CLAIMABLE_TRANCHE_EXPIRY_DESTINATION_TERMS_AND_EXACT_AUTHENTICATED_CLAIM_FLOW",
    "known_cost_or_risk": (
        "The published manual-claim flow does not require a new trade or deposit, but receiving $GRVT is a financial asset receipt and can create market-value, custody, recordkeeping and tax consequences depending on the user's circumstances. "
        "Each unlocked batch has a 30-day claim window and can expire. The two current official TGE help articles disagree on the registration deadline, so public documentation alone cannot establish this account's eligibility. "
        "Any later transfer, withdrawal or bridge of claimed $GRVT is a separate asset-movement action and is not authorized by this path."
    ),
    "missing_approval": (
        "A supported already-authenticated GRVT session; confirmation in the Reward Portal that this account has a currently claimable released tranche; the tranche amount, release date, 30-day expiry, credit destination and exact confirmation/signing requirements; current Terms/jurisdiction/account eligibility; and explicit approval to receive the $GRVT financial reward."
    ),
    "next_action": (
        "In a supported already-authenticated GRVT session, inspect the Reward Portal read-only and record the currently claimable tranche amount, release date, expiry, destination and exact confirmation/signing requirements. "
        "If a tranche is claimable, keep the actual Claim click in explicit financial approval. Do not click Claim, connect/sign a wallet, deposit, withdraw, bridge, transfer tokens or place any real order automatically."
    ),
    "action_taken": "NONE",
    "auto_executed": False,
    "points_delta": None,
}


def _verified_at_is_fresh(verified_at: str, *, now: datetime) -> bool:
    verified = datetime.fromisoformat(verified_at).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=VERIFICATION_TTL_DAYS)


def apply_grvt_tge_claim_path(report: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Add the current GRVT TGE claim as approval-only; never execute the claim."""
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    paths = result.setdefault("additional_approval_paths", [])
    if not isinstance(paths, list):
        return result

    active_slugs = {
        str(action.get("slug"))
        for action in result.get("actions", [])
        if isinstance(action, dict)
    }
    already_present = any(
        isinstance(path, dict) and path.get("slug") == GRVT_TGE_CLAIM_PATH["slug"]
        for path in paths
    )
    if (
        already_present
        or GRVT_TGE_CLAIM_PATH["parent_slug"] not in active_slugs
        or not _verified_at_is_fresh(GRVT_TGE_CLAIM_VERIFIED_AT, now=current)
    ):
        return result

    expires = (
        datetime.fromisoformat(GRVT_TGE_CLAIM_VERIFIED_AT).astimezone(UTC)
        + timedelta(days=VERIFICATION_TTL_DAYS)
    )
    path = copy.deepcopy(GRVT_TGE_CLAIM_PATH)
    path.update(
        {
            "evidence_status": "PRIMARY_VERIFIED_CURRENT",
            "verification_expires_at": expires.isoformat(),
        }
    )
    paths.append(path)

    result["reward_path_count"] = int(
        result.get("reward_path_count", len(result.get("actions", [])))
    ) + 1
    result["verified_additional_path_count"] = int(
        result.get("verified_additional_path_count", 0)
    ) + 1
    result["additional_approval_required_count"] = int(
        result.get("additional_approval_required_count", 0)
    ) + 1
    result["approval_required_count"] = int(result.get("approval_required_count", 0)) + 1
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply current GRVT TGE released-tranche approval-only claim path"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    result = apply_grvt_tge_claim_path(report)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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
