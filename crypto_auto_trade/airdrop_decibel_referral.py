from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_REFERRAL_VERIFIED_AT = "2026-08-17T07:02:37+00:00"
DECIBEL_REFERRAL_SOURCE = "https://docs.decibel.trade/rewards/referral-program"
DECIBEL_REWARDS_OVERVIEW_SOURCE = "https://docs.decibel.trade/rewards/overview"
DECIBEL_ANNOUNCEMENTS_SOURCE = "https://app.decibel.trade/announcements"
DECIBEL_TERMS_SOURCE = "https://decibel.trade/terms-of-service"

DECIBEL_REFERRAL_PATH: dict[str, Any] = {
    "parent_slug": "decibel-trading",
    "slug": "decibel-referral-amps",
    "name": "Decibel Referral Rewards Path",
    "verified_at": DECIBEL_REFERRAL_VERIFIED_AT,
    "evidence_source": DECIBEL_ANNOUNCEMENTS_SOURCE,
    "evidence_sources": [
        DECIBEL_ANNOUNCEMENTS_SOURCE,
        DECIBEL_REFERRAL_SOURCE,
        DECIBEL_REWARDS_OVERVIEW_SOURCE,
        DECIBEL_TERMS_SOURCE,
    ],
    "source_coverage": "PRIMARY_OFFICIAL_SOURCES_WITH_INTERNAL_TEMPORAL_CONFLICT_NO_INDEPENDENT_EXPERT_SOURCE",
    "evidence_note": (
        "Current official Decibel sources agree that referral rewards remain available at a 10% share, but the public onboarding/code model is temporally inconsistent across official pages. "
        "The newer June 3, 2026 official product announcement says Decibel is no longer invite-only, new users do not need a referral code, every user has one reusable referral code with unlimited uses, and referrers earn 10% of referees' points. "
        "The Referral Program documentation still describes the earlier Mainnet Beta flow of five one-time codes unlocked after $25,000 of trading volume and 10% of invitees' Amps. "
        "Because the newer product announcement explicitly says the old invite-code model changed, this agent must not treat the $25,000 trading threshold or five-code limit as a current prerequisite without an authenticated current-account check. "
        "Current Decibel Terms keep referrals personal and non-commercial: codes may only be shared with people the participant personally knows, the incentive must be disclosed, express consent is required before sharing, and self-referral, farming, spam, bots, mass outreach, paid advertising, deceptive promotion and manipulation are prohibited."
    ),
    "published_referral_share_pct": 10,
    "legacy_beta_volume_threshold_usd": 25000,
    "legacy_beta_referral_code_count": 5,
    "newer_public_referral_code_model": "ONE_REUSABLE_CODE_UNLIMITED_USES_NO_INVITE_REQUIRED",
    "current_trading_threshold_required": None,
    "public_rule_status": "CONFLICT_NEWER_PRODUCT_ANNOUNCEMENT_SUPERSEDES_BETA_INVITE_FLOW_REVERIFY_AUTHENTICATED",
    "account_specific_code_status": "UNKNOWN_UNTIL_AUTHENTICATED",
    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
    "requires_user_approval": True,
    "requires_funds": False,
    "requires_wallet_signature": True,
    "wallet_signature_requirement": "FAIL_CLOSED_UNTIL_AUTHENTICATED_WALLET_CONNECTION_FLOW_IS_VERIFIED",
    "requires_real_order": False,
    "requires_asset_move": False,
    "requires_external_communication": True,
    "authentication_recheck_required": True,
    "terms_status": "REVERIFY_CURRENT_TERMS_JURISDICTION_ACCOUNT_REFERRAL_SURFACE_CODE_ELIGIBILITY_AND_WALLET_AUTHENTICATION",
    "prohibited_methods": [
        "self_referral",
        "multi_account_farming",
        "wash_or_self_trading",
        "manufactured_volume",
        "spam_or_mass_outreach",
        "bots_or_automated_referral_messaging",
        "paid_advertising_for_referral_codes",
        "deceptive_or_undisclosed_incentive_promotion",
        "contact_scraping_or_direct_marketing_without_consent",
    ],
    "known_cost_or_risk": (
        "Do not incur trading volume merely to unlock referral codes based on the older Mainnet Beta documentation. The newer official product announcement says the invite-only model ended and every user has one reusable referral code, so any current trading-volume prerequisite is unverified until the authenticated account surface proves otherwise. "
        "Referral sharing is not a general automated-growth action: current Terms restrict referrals to personally known individuals, require disclosure of the incentive and express consent before sharing, and prohibit self-referral, farming, spam, bots, mass outreach, paid ads and manipulative activity. "
        "The public sources use both 'points' and 'Amps' wording for the 10% referral reward; no cash value or profitability is assumed, and Decibel may modify, suspend or disqualify promotional rewards under its Terms."
    ),
    "missing_approval": (
        "A supported authenticated Decibel session to inspect the current referral surface, confirm whether a reusable referral code already exists, determine the current reward denomination and account eligibility, and verify the exact wallet authentication/signing behavior. "
        "Do not create trading volume to unlock codes unless the authenticated current product surface and current Terms explicitly show that a trading threshold still applies. "
        "Any referral communication requires a specifically identified personally known recipient, evidence of express consent before sharing, and explicit communication approval; no automated outreach is authorized."
    ),
    "next_action": (
        "In a supported authenticated Decibel session, perform a read-only check of the current referral-code/link surface and wallet/authentication flow. "
        "If a reusable code already exists, record its availability privately and keep all sharing in a separate human-approved personal-referral step that complies with disclosure and express-consent requirements. "
        "If the authenticated current product unexpectedly shows a trading prerequisite, record that as a new primary-source fact and prepare a capped plan for explicit financial approval; do not trade, sign a wallet message, move assets, self-refer, message contacts, scrape contact lists, run ads or manufacture volume automatically."
    ),
    "action_taken": "NONE",
    "auto_executed": False,
    "points_delta": None,
}


def _verified_at_is_fresh(verified_at: str, *, now: datetime) -> bool:
    verified = datetime.fromisoformat(verified_at).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=VERIFICATION_TTL_DAYS)


def apply_decibel_referral_path(report: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Append current Decibel referral metadata as approval-only; never execute it."""
    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    paths = result.setdefault("additional_approval_paths", [])
    if not isinstance(paths, list):
        return result

    active_slugs = {str(action.get("slug")) for action in result.get("actions", []) if isinstance(action, dict)}
    already_present = any(isinstance(path, dict) and path.get("slug") == DECIBEL_REFERRAL_PATH["slug"] for path in paths)
    if already_present or DECIBEL_REFERRAL_PATH["parent_slug"] not in active_slugs:
        return result
    if not _verified_at_is_fresh(DECIBEL_REFERRAL_VERIFIED_AT, now=current):
        return result

    expires = datetime.fromisoformat(DECIBEL_REFERRAL_VERIFIED_AT).astimezone(UTC) + timedelta(days=VERIFICATION_TTL_DAYS)
    path = copy.deepcopy(DECIBEL_REFERRAL_PATH)
    path.update(
        {
            "evidence_status": "PRIMARY_VERIFIED_CURRENT_WITH_OFFICIAL_SOURCE_CONFLICT",
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
    parser = argparse.ArgumentParser(description="Apply current Decibel referral approval-only reward path")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    result = apply_decibel_referral_path(report)
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
