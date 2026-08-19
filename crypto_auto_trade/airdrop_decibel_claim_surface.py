from __future__ import annotations

import argparse
import copy
import html
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_CLAIM_SURFACE_VERIFIED_AT = "2026-08-19T10:16:46+00:00"
DECIBEL_LIVE_CAMPAIGNS_SOURCE = "https://docs.decibel.trade/rewards/campaigns/live"
DECIBEL_REWARDS_OVERVIEW_SOURCE = "https://docs.decibel.trade/rewards/overview"
DECIBEL_REWARDS_FAQ_SOURCE = "https://docs.decibel.trade/rewards/faq"
DECIBEL_REWARDS_APP_SOURCE = "https://app.decibel.trade/rewards"
DECIBEL_TERMS_SOURCE = "https://decibel.trade/terms-of-service"

_REQUIRED_CURRENT_SOURCES = (
    DECIBEL_LIVE_CAMPAIGNS_SOURCE,
    DECIBEL_REWARDS_OVERVIEW_SOURCE,
    DECIBEL_REWARDS_FAQ_SOURCE,
)

# Manually reviewed primary-source snapshot. Decibel's current Terms prohibit
# automated access to the Services, so neither the scheduled workflow nor this
# module performs a Decibel HTTP fetch. The snapshot may only inform approval
# metadata and is TTL-gated; it can never authorize a financial/signing action.
_SNAPSHOT_SOURCE_TEXTS = {
    DECIBEL_LIVE_CAMPAIGNS_SOURCE: (
        "Active now — distributing rewards today. The campaigns below are live. "
        "The /rewards page is coming soon; in the meantime, active rewards are delivered "
        "via Claim now pop-ups inside the Decibel app. Once /rewards ships, users will be "
        "able to review and claim all eligible rewards from one page."
    ),
    DECIBEL_REWARDS_OVERVIEW_SOURCE: (
        "Campaign rewards are claimed through the /rewards page (coming soon) and credited "
        "directly to the trading account in a single onchain transaction."
    ),
    DECIBEL_REWARDS_FAQ_SOURCE: (
        "You'll see the expiry date on each tile in /rewards. New campaigns appear on the "
        "/rewards page."
    ),
    DECIBEL_REWARDS_APP_SOURCE: "Account-specific reward state requires authentication.",
}

_AUTOMATED_ACCESS_BLOCK_REASON = "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED"


def _is_fresh(*, now: datetime) -> bool:
    verified = datetime.fromisoformat(DECIBEL_CLAIM_SURFACE_VERIFIED_AT).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=VERIFICATION_TTL_DAYS)


def _normalize_document(raw: str) -> str:
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.lower().split())


def _classify_claim_surface(source_texts: dict[str, str]) -> str:
    live = _normalize_document(source_texts.get(DECIBEL_LIVE_CAMPAIGNS_SOURCE, ""))
    overview = _normalize_document(source_texts.get(DECIBEL_REWARDS_OVERVIEW_SOURCE, ""))
    faq = _normalize_document(source_texts.get(DECIBEL_REWARDS_FAQ_SOURCE, ""))

    live_current = (
        "review and claim all eligible rewards from the /rewards page" in live
        and "distributing rewards today" in live
    )
    live_coming_soon = (
        "/rewards page is coming soon" in live
        or "the /rewards page is coming soon" in live
        or "/rewards is coming soon" in live
    )
    overview_current = (
        "campaign rewards are claimed through the /rewards page" in overview
        and "single onchain transaction" in overview
    )
    faq_current = (
        "expiry date on each tile in /rewards" in faq
        and "appear on the /rewards page" in faq
    )

    if live_coming_soon:
        return "CONFLICT_FAIL_CLOSED"
    if live_current and overview_current and faq_current:
        return "CURRENT_REWARDS_PAGE"
    return "UNVERIFIED_FAIL_CLOSED"


def _fetch_url(url: str, *, timeout_seconds: float = 12.0) -> str:
    """Compatibility shim that intentionally never performs network access."""
    del url, timeout_seconds
    raise RuntimeError(_AUTOMATED_ACCESS_BLOCK_REASON)


def fetch_decibel_claim_sources() -> tuple[dict[str, str], dict[str, str]]:
    """Fail closed instead of automating Decibel access under the current Terms."""
    errors = {
        url: _AUTOMATED_ACCESS_BLOCK_REASON
        for url in (
            DECIBEL_LIVE_CAMPAIGNS_SOURCE,
            DECIBEL_REWARDS_OVERVIEW_SOURCE,
            DECIBEL_REWARDS_FAQ_SOURCE,
            DECIBEL_REWARDS_APP_SOURCE,
        )
    }
    return {}, errors


def apply_decibel_claim_surface(
    report: dict[str, Any],
    *,
    now: datetime | None = None,
    source_texts: dict[str, str] | None = None,
    evidence_checked_at: datetime | None = None,
    fetch_errors: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Refresh claim metadata without executing a claim, wallet action, or HTTP fetch."""
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["decibel_claim_surface_override_count"] = 0

    externally_supplied_evidence = source_texts is not None
    if not externally_supplied_evidence and not _is_fresh(now=current):
        return result

    evidence = source_texts if externally_supplied_evidence else _SNAPSHOT_SOURCE_TEXTS
    checked = (
        (evidence_checked_at or current)
        if externally_supplied_evidence
        else datetime.fromisoformat(DECIBEL_CLAIM_SURFACE_VERIFIED_AT)
    ).astimezone(UTC)
    classification = _classify_claim_surface(evidence)
    errors = fetch_errors or {}
    missing_required = [url for url in _REQUIRED_CURRENT_SOURCES if not evidence.get(url)]
    expires = checked + timedelta(
        hours=2 if externally_supplied_evidence else 24 * VERIFICATION_TTL_DAYS
    )

    paths = result.get("additional_approval_paths", [])
    if not isinstance(paths, list):
        return result

    for path in paths:
        if not isinstance(path, dict) or path.get("slug") != "decibel-campaign-claims":
            continue
        if path.get("acquisition_state") != "APPROVAL_REQUIRED_FINANCIAL":
            continue

        common = {
            "verified_at": checked.isoformat(),
            "evidence_checked_at": checked.isoformat(),
            "evidence_source": DECIBEL_LIVE_CAMPAIGNS_SOURCE,
            "evidence_sources": [
                DECIBEL_LIVE_CAMPAIGNS_SOURCE,
                DECIBEL_REWARDS_OVERVIEW_SOURCE,
                DECIBEL_REWARDS_FAQ_SOURCE,
                DECIBEL_REWARDS_APP_SOURCE,
                DECIBEL_TERMS_SOURCE,
            ],
            "verification_expires_at": expires.isoformat(),
            "terms_status": (
                "CURRENT_PUBLIC_TERMS_REVIEWED_REVERIFY_ACCOUNT_JURISDICTION_"
                "ELIGIBILITY_REWARD_AMOUNT_EXPIRY_AND_CLAIM_SIGNING"
            ),
            "automation_permitted": False,
            "automation_block_reason": _AUTOMATED_ACCESS_BLOCK_REASON,
            "action_taken": "NONE",
            "auto_executed": False,
            "points_delta": None,
        }

        if classification == "CURRENT_REWARDS_PAGE":
            path.update(
                {
                    **common,
                    "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                    "evidence_note": (
                        "Externally supplied current primary Decibel evidence states that active campaigns "
                        "can be reviewed and claimed through /rewards, with in-app 'Claim now' notifications "
                        "as an additional surface. Rewards Overview describes a single onchain claim transaction "
                        "and the FAQ refers to campaign tiles on /rewards. This establishes only the public claim "
                        "route, not account-specific eligibility or a claimable amount."
                    ),
                    "claim_surface_status": (
                        "CURRENT_REWARDS_PAGE_AND_IN_APP_CLAIM_NOW_CONFIRMED"
                    ),
                    "known_cost_or_risk": (
                        "An actual campaign claim is a financial receipt and may require wallet/onchain "
                        "authorization. Account eligibility, reward amount, asset, expiry, signing requirements "
                        "and network cost remain unknown until an authenticated human-reviewed account surface "
                        "is available. Decibel campaign parameters can change and unclaimed rewards can expire."
                    ),
                    "missing_approval": (
                        "Human-reviewed current Terms/jurisdiction and account eligibility; a supported already-"
                        "authenticated Decibel session showing a Ready to Claim reward, amount, asset and expiry; "
                        "the exact signing/onchain requirements and network cost; and explicit approval to receive "
                        "the financial reward."
                    ),
                    "next_action": (
                        "Use a supported already-authenticated session only for human/read-only account inspection. "
                        "If a reward is Ready to Claim, record amount, asset, expiry and signing/onchain requirements "
                        "and keep the actual claim in explicit financial approval. Do not automate Decibel access, "
                        "connect/sign a wallet, submit a claim, trade, deposit, withdraw or move assets."
                    ),
                    "claim_status": (
                        "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_REWARDS_PAGE_OR_IN_APP_NOTIFICATION"
                    ),
                }
            )
        elif classification == "CONFLICT_FAIL_CLOSED":
            path.update(
                {
                    **common,
                    "evidence_status": "PRIMARY_VERIFIED_CURRENT_CONFLICT_FAIL_CLOSED",
                    "evidence_note": (
                        "Current manually reviewed primary Decibel claim documentation contains a current/future "
                        "claim-surface conflict. Live Campaigns says /rewards is coming soon and active rewards are "
                        "delivered through in-app 'Claim now' pop-ups, while Overview/FAQ and campaign details still "
                        "refer to /rewards. The agent therefore fails closed to the authenticated in-app notification "
                        "and does not treat /rewards as a current acquisition route."
                    ),
                    "claim_surface_status": (
                        "CURRENT_IN_APP_CLAIM_NOW_CONFIRMED_REWARDS_PAGE_CONFLICT_UNVERIFIED"
                    ),
                    "known_cost_or_risk": (
                        "No new trade or deposit is required merely to inspect an already-earned notification, but "
                        "an actual campaign claim is a financial receipt and may require an onchain transaction or "
                        "wallet authorization. Account-specific eligibility, amount, asset, expiry, signing "
                        "requirements and network cost remain unknown."
                    ),
                    "missing_approval": (
                        "A human-reviewed supported already-authenticated Decibel session showing an account-specific "
                        "in-app 'Claim now' notification; current Terms/jurisdiction eligibility; reward amount, asset "
                        "and expiry; exact transaction/signing requirements and network cost; and explicit approval "
                        "to receive the financial reward."
                    ),
                    "next_action": (
                        "Do not automate Decibel access. When a supported already-authenticated session is available, "
                        "inspect only the current in-app 'Claim now' notification. If a reward is claimable, record "
                        "amount, asset, expiry and signing requirements and keep the actual claim in explicit financial "
                        "approval. Do not connect/sign a wallet or submit a claim transaction automatically."
                    ),
                    "claim_status": (
                        "ACCOUNT_SPECIFIC_UNKNOWN_UNTIL_AUTHENTICATED_IN_APP_CLAIM_NOW_NOTIFICATION"
                    ),
                }
            )
        else:
            error_summary = "; ".join(
                f"{url}: {errors.get(url, 'missing')}" for url in missing_required
            )
            path.update(
                {
                    **common,
                    "evidence_status": "CURRENT_PRIMARY_RECHECK_INCOMPLETE_FAIL_CLOSED",
                    "evidence_note": (
                        "The supplied review evidence is incomplete, so the claim surface remains unverified and "
                        "the agent fails closed without inferring or executing a claim route."
                        + (f" Missing/error sources: {error_summary}" if error_summary else "")
                    ),
                    "claim_surface_status": "REVERIFY_REQUIRED_CURRENT_CLAIM_SURFACE",
                    "known_cost_or_risk": (
                        "Claim-route state is unverified. Any actual reward claim is a financial receipt and may "
                        "require wallet authorization/onchain execution; account eligibility, amount, asset, expiry "
                        "and network cost are not established."
                    ),
                    "missing_approval": (
                        "A fresh human/manual review of current Decibel primary documentation, followed by a supported "
                        "already-authenticated session, current Terms/jurisdiction eligibility, account-specific "
                        "claimable reward details, exact transaction/signing requirements and explicit approval to "
                        "receive the financial reward."
                    ),
                    "next_action": (
                        "Perform a human/manual primary-source review outside the automated Decibel service path. "
                        "Only after the current claim surface is resolved should an already-authenticated session be "
                        "inspected read-only. Do not automate Decibel HTTP access, connect/sign a wallet or submit a "
                        "claim transaction automatically."
                    ),
                    "claim_status": "REVERIFY_REQUIRED_BEFORE_ACCOUNT_INSPECTION",
                }
            )

        result["decibel_claim_surface_override_count"] = 1
        result["decibel_claim_surface_live_recheck"] = externally_supplied_evidence
        result["decibel_claim_surface_fetch_error_count"] = len(errors)
        result["decibel_automated_access_blocked"] = True
        break

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply manually reviewed cached Decibel campaign claim metadata without automated Decibel access"
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    updated = apply_decibel_claim_surface(report, now=datetime.now(UTC))
    args.output.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "decibel_claim_surface_override_count": updated.get(
                    "decibel_claim_surface_override_count", 0
                ),
                "live_recheck": False,
                "automated_access_blocked": True,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
