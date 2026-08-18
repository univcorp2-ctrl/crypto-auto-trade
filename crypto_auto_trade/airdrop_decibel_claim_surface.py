from __future__ import annotations

import argparse
import copy
import html
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_CLAIM_SURFACE_VERIFIED_AT = "2026-08-18T15:21:42+00:00"
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

# Deterministic fallback used by unit tests and library callers that do not opt into
# network re-verification. The CLI used by GitHub Actions fetches the current primary
# sources on every run and passes them to apply_decibel_claim_surface().
_SNAPSHOT_SOURCE_TEXTS = {
    DECIBEL_LIVE_CAMPAIGNS_SOURCE: (
        "Active now — distributing rewards today. The campaigns below are live. "
        "Review and claim all eligible rewards from the /rewards page in the Decibel app; "
        "you may also see Claim now pop-ups surfacing rewards as you trade."
    ),
    DECIBEL_REWARDS_OVERVIEW_SOURCE: (
        "Campaign rewards are claimed through the /rewards page and credited directly to "
        "your trading account balance in a single onchain transaction."
    ),
    DECIBEL_REWARDS_FAQ_SOURCE: (
        "You'll see the expiry date on each tile in /rewards. New campaigns appear on the "
        "/rewards page."
    ),
    DECIBEL_REWARDS_APP_SOURCE: "Rewards. Must connect a wallet first.",
}


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
    request = Request(
        url,
        headers={
            "User-Agent": "crypto-auto-trade-airdrop-agent/1.0 (+https://github.com/univcorp2-ctrl/crypto-auto-trade)"
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_decibel_claim_sources() -> tuple[dict[str, str], dict[str, str]]:
    """Fetch current public Decibel claim documentation; never authenticate or sign."""
    source_texts: dict[str, str] = {}
    errors: dict[str, str] = {}
    for url in (
        DECIBEL_LIVE_CAMPAIGNS_SOURCE,
        DECIBEL_REWARDS_OVERVIEW_SOURCE,
        DECIBEL_REWARDS_FAQ_SOURCE,
        DECIBEL_REWARDS_APP_SOURCE,
    ):
        try:
            source_texts[url] = _fetch_url(url)
        except Exception as exc:  # Network failures fail closed instead of aborting safety metadata.
            errors[url] = f"{type(exc).__name__}: {exc}"
    return source_texts, errors


def apply_decibel_claim_surface(
    report: dict[str, Any],
    *,
    now: datetime | None = None,
    source_texts: dict[str, str] | None = None,
    evidence_checked_at: datetime | None = None,
    fetch_errors: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Refresh Decibel claim metadata without executing any claim or wallet action."""
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["decibel_claim_surface_override_count"] = 0

    live_recheck = source_texts is not None
    if not live_recheck and not _is_fresh(now=current):
        return result

    evidence = source_texts if live_recheck else _SNAPSHOT_SOURCE_TEXTS
    checked = (
        (evidence_checked_at or current)
        if live_recheck
        else datetime.fromisoformat(DECIBEL_CLAIM_SURFACE_VERIFIED_AT)
    ).astimezone(UTC)
    classification = _classify_claim_surface(evidence)
    errors = fetch_errors or {}
    missing_required = [url for url in _REQUIRED_CURRENT_SOURCES if not evidence.get(url)]
    expires = checked + timedelta(hours=2 if live_recheck else 24 * VERIFICATION_TTL_DAYS)

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
                        "Current official Decibel Live Campaigns says the listed campaigns are active "
                        "and distributing rewards today and explicitly directs eligible users to review "
                        "and claim rewards from the /rewards page, with in-app 'Claim now' pop-ups as an "
                        "additional notification surface. The current Rewards Overview independently "
                        "states that campaign rewards are claimed through /rewards and credited to the "
                        "trading account in a single onchain transaction, while the current FAQ refers "
                        "to expiry tiles and new campaigns on /rewards. The public /rewards application "
                        "route is deployed and requires wallet connection before account-specific reward "
                        "data is shown. These current primary sources establish the live claim route but "
                        "do not prove this account has an eligible or claimable reward."
                    ),
                    "claim_surface_status": (
                        "CURRENT_REWARDS_PAGE_AND_IN_APP_CLAIM_NOW_CONFIRMED"
                    ),
                    "known_cost_or_risk": (
                        "No new trade or deposit is required merely to inspect an already-earned campaign "
                        "reward, but an actual campaign claim is a financial receipt. Current Decibel "
                        "documentation says a Ready to Claim reward is credited to the trading account in "
                        "a single onchain transaction, and the public /rewards route requires wallet "
                        "connection. Account-specific eligibility, reward amount, asset, expiry, exact "
                        "transaction/signing requirements and any network cost remain unknown before "
                        "authenticated inspection; reward parameters and claim windows can change, and "
                        "unclaimed rewards can expire. Decibel's current Terms make Campaign Rules and "
                        "jurisdictional compliance controlling. Receiving a USD-denominated stablecoin "
                        "reward can also create recordkeeping or tax obligations depending on the user's "
                        "circumstances; no tax conclusion is assumed here."
                    ),
                    "missing_approval": (
                        "A supported already-authenticated Decibel account/wallet session for read-only "
                        "inspection; confirmation that the account is eligible under current Terms and "
                        "jurisdiction; an account-specific Ready to Claim reward showing amount, asset and "
                        "expiry; confirmation of the exact onchain transaction/signing requirements and any "
                        "network cost; and explicit approval to receive the financial reward."
                    ),
                    "next_action": (
                        "In a supported already-authenticated Decibel session, inspect /rewards and the "
                        "in-app unclaimed-rewards banner for account-specific eligibility, Ready to Claim "
                        "status, reward amount, asset, expiry and exact signing/onchain requirements. If a "
                        "reward is Ready to Claim, record those details and keep the actual claim in explicit "
                        "financial approval. Do not connect/sign a wallet, submit a claim transaction, trade, "
                        "deposit, withdraw or move assets automatically."
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
                        "Current primary Decibel claim documentation contains a current/future claim-surface "
                        "conflict. The agent fails closed to the authenticated in-app 'Claim now' notification "
                        "and does not treat /rewards as a current acquisition route until current-state "
                        "documentation or the authenticated account surface resolves the conflict."
                    ),
                    "claim_surface_status": (
                        "CURRENT_IN_APP_CLAIM_NOW_CONFIRMED_REWARDS_PAGE_CONFLICT_UNVERIFIED"
                    ),
                    "known_cost_or_risk": (
                        "No new trade or deposit is required merely to inspect an already-earned campaign "
                        "notification, but an actual campaign claim is a financial receipt and may require an "
                        "onchain transaction or wallet authorization. Account-specific eligibility, amount, "
                        "asset, expiry, signing requirements and network cost remain unknown."
                    ),
                    "missing_approval": (
                        "A supported already-authenticated Decibel session for read-only inspection of the "
                        "current in-app unclaimed-reward banner/'Claim now' notification; current Terms and "
                        "jurisdiction eligibility; account-specific reward amount, asset and expiry; exact "
                        "transaction/signing requirements and network cost; and explicit approval to receive "
                        "the financial reward."
                    ),
                    "next_action": (
                        "Inspect only the current authenticated in-app 'Claim now' notification until current "
                        "primary documentation or the authenticated account surface resolves the /rewards "
                        "conflict. If a reward is claimable, record the details and keep the actual claim in "
                        "explicit financial approval. Do not connect/sign a wallet or submit a claim "
                        "transaction automatically."
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
                        "The live read-only recheck did not obtain enough current primary Decibel evidence "
                        "to establish the current campaign claim surface. The agent therefore fails closed "
                        "and does not execute or infer any claim route."
                        + (f" Missing/error sources: {error_summary}" if error_summary else "")
                    ),
                    "claim_surface_status": "REVERIFY_REQUIRED_CURRENT_CLAIM_SURFACE",
                    "known_cost_or_risk": (
                        "Claim-route state is currently unverified. Any actual reward claim is a financial "
                        "receipt and may require wallet authorization/onchain execution; account eligibility, "
                        "amount, asset, expiry and network cost are not established."
                    ),
                    "missing_approval": (
                        "Successful current primary-source re-verification, followed by a supported "
                        "already-authenticated Decibel session, current Terms/jurisdiction eligibility, "
                        "account-specific claimable reward details, exact transaction/signing requirements "
                        "and explicit approval to receive the financial reward."
                    ),
                    "next_action": (
                        "Re-fetch current Decibel Live Campaigns, Rewards Overview and FAQ. Only after those "
                        "primary sources establish the current claim surface should an already-authenticated "
                        "session be inspected read-only. Do not connect/sign a wallet or submit a claim "
                        "transaction automatically."
                    ),
                    "claim_status": "REVERIFY_REQUIRED_BEFORE_ACCOUNT_INSPECTION",
                }
            )

        result["decibel_claim_surface_override_count"] = 1
        result["decibel_claim_surface_live_recheck"] = live_recheck
        result["decibel_claim_surface_fetch_error_count"] = len(errors)
        break

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh current Decibel campaign claim-surface metadata without executing claims"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    checked_at = datetime.now(UTC)
    source_texts, fetch_errors = fetch_decibel_claim_sources()
    updated = apply_decibel_claim_surface(
        report,
        now=checked_at,
        source_texts=source_texts,
        evidence_checked_at=checked_at,
        fetch_errors=fetch_errors,
    )
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
                "live_recheck": updated.get("decibel_claim_surface_live_recheck", False),
                "fetch_error_count": updated.get("decibel_claim_surface_fetch_error_count", 0),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
