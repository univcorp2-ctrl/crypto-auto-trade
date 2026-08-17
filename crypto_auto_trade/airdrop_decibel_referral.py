from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import VERIFICATION_TTL_DAYS

DECIBEL_REFERRAL_VERIFIED_AT = "2026-08-17T06:38:35+00:00"
DECIBEL_REFERRAL_SOURCE = "https://docs.decibel.trade/rewards/referral-program"
DECIBEL_REWARDS_OVERVIEW_SOURCE = "https://docs.decibel.trade/rewards/overview"
DECIBEL_TERMS_SOURCE = "https://decibel.trade/terms-of-service"

DECIBEL_REFERRAL_PATH: dict[str, Any] = {
    "parent_slug": "decibel-trading",
    "slug": "decibel-referral-amps",
    "name": "Decibel Referral Amps Path",
    "verified_at": DECIBEL_REFERRAL_VERIFIED_AT,
    "evidence_source": DECIBEL_REFERRAL_SOURCE,
    "evidence_sources": [
        DECIBEL_REFERRAL_SOURCE,
        DECIBEL_REWARDS_OVERVIEW_SOURCE,
        DECIBEL_TERMS_SOURCE,
    ],
    "source_coverage": "PRIMARY_OFFICIAL_PROGRAM_PLUS_CURRENT_TERMS_NO_INDEPENDENT_EXPERT_SOURCE",
    "evidence_note": (
        "Current official Decibel Referral Program documentation says a referrer earns 10% of referred users' Amps from a dedicated daily emission pool. "
        "The current public qualification flow says a wallet receives five referral codes after connecting the wallet and completing $25,000 of trading volume; referred users bind a code at initial wallet connection, and referral Amps update daily based on the invitees' bona fide trading activity rather than signups alone. "
        "Current Decibel Terms make the referral program personal and non-commercial: codes may only be shared with people the participant personally knows, the participant must disclose the incentive and obtain express consent before sharing, and self-referral, multi-account farming, spam, bots, mass outreach, paid advertising, deceptive promotion and manipulation are prohibited."
    ),
    "reward_share_pct_of_invitee_amps": 10,
    "published_volume_threshold_usd": 25000,
    "initial_referral_code_count": 5,
    "account_specific_code_status": "UNKNOWN_UNTIL_AUTHENTICATED",
    "historical_volume_may_already_satisfy_threshold": True,
    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
    "requires_user_approval": True,
    "requires_funds": True,
    "requires_wallet_signature": True,
    "wallet_signature_requirement": "FAIL_CLOSED_UNTIL_AUTHENTICATED_WALLET_CONNECTION_FLOW_IS_VERIFIED",
    "requires_real_order": True,
    "requires_asset_move": False,
    "requires_external_communication": True,
    "authentication_recheck_required": True,
    "terms_status": "REVERIFY_CURRENT_TERMS_JURISDICTION_ACCOUNT_REFERRAL_CODE_ELIGIBILITY_HISTORICAL_VOLUME_AND_WALLET_AUTHENTICATION",
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
        "If the account has not already met the published $25,000 trading-volume threshold, unlocking referral codes requires additional genuine trading and therefore fees, spread/slippage, funding, margin/liquidation and directional PnL risk. "
        "Even if referral codes are already available from historical activity, sharing them is not a general automated-growth action: current Terms restrict referrals to personally known individuals, require disclosure of the referrer's incentive and express consent before sharing, and prohibit self-referral, farming, spam, bots, mass outreach, paid ads and manipulative activity. "
        "The 10% reward is denominated in Amps rather than verified cash value and depends on referred users' bona fide activity; Decibel may modify, suspend or disqualify promotional rewards under its Terms."
    ),
    "missing_approval": (
        "A supported authenticated Decibel session to check whether referral codes already exist and whether historical volume has satisfied the $25,000 threshold; current Terms/jurisdiction and account eligibility; and the exact wallet authentication/signing behavior. "
        "If the threshold is unmet, any additional trading requires explicit market, maximum notional, leverage, fee/funding budget and maximum acceptable loss approval. "
        "If codes already exist, any referral communication requires a specifically identified personally known recipient, evidence of express consent before sharing, and explicit communication approval; no automated outreach is authorized."
    ),
    "next_action": (
        "In a supported authenticated Decibel session, perform a read-only check of referral-code availability, historical qualifying volume and the current wallet/authentication flow. "
        "If codes are already available, record them privately and keep all sharing in a separate human-approved personal-referral step that complies with disclosure and express-consent requirements. "
        "If the $25,000 threshold is not met, keep any genuine-trading plan in explicit financial approval; do not trade, sign a wallet message, move assets, self-refer, message contacts, scrape contact lists, run ads or manufacture volume automatically."
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
    """Append the current Decibel referral path as approval-only metadata; never execute it."""
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
            "evidence_status": "PRIMARY_VERIFIED_CURRENT",
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
    parser = argparse.ArgumentParser(description="Apply current Decibel referral Amps approval-only reward path")
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
