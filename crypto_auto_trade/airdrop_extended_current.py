from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_live_overrides import OVERRIDE_TTL_DAYS


EXTENDED_VERIFIED_AT = "2026-08-19T08:22:54+00:00"
EXTENDED_POINTS_SOURCE = "https://docs.extended.exchange/extended-resources/points"
EXTENDED_RESTRICTED_SOURCE = "https://docs.extended.exchange/extended-resources/legal/restricted-countries"
EXTENDED_TERMS_SOURCE = "https://docs.extended.exchange/extended-resources/legal/terms-of-use"
EXTENDED_API_SOURCE = "https://api.docs.extended.exchange/"
EXTENDED_VAULT_SOURCE = "https://docs.extended.exchange/extended-resources/vault"
EXTENDED_MIGRATION_SOURCE = "https://docs.extended.exchange/starknet-migration/migration-guide"
EXTENDED_REFERRAL_SOURCE = "https://docs.extended.exchange/extended-resources/referrals-and-affiliates"
APPROVAL_STATES = {"APPROVAL_REQUIRED_FINANCIAL", "APPROVAL_REQUIRED_ASSET_MOVE"}
EXTENDED_APPROVAL_STATES = {
    "extended-trading": "APPROVAL_REQUIRED_FINANCIAL",
    "extended-liquidity": "APPROVAL_REQUIRED_ASSET_MOVE",
}


def _is_fresh(*, now: datetime) -> bool:
    verified = datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=OVERRIDE_TTL_DAYS)


def _verification_expires_at() -> str:
    return (
        datetime.fromisoformat(EXTENDED_VERIFIED_AT).astimezone(UTC)
        + timedelta(days=OVERRIDE_TTL_DAYS)
    ).isoformat()


def _refresh_status_counts(report: dict[str, Any]) -> None:
    targets = [item for item in report.get("targets", []) if isinstance(item, dict)]
    report["ready_dry_run"] = sum(item.get("status") == "READY_DRY_RUN" for item in targets)
    report["read_only"] = sum(item.get("status") == "READ_ONLY" for item in targets)
    report["unverified"] = sum(item.get("status") == "UNVERIFIED" for item in targets)


def apply_extended_current_status(
    report: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Propagate current Extended evidence to public/manual status without executing.

    A harder fail-closed state always wins. Fresh evidence can mark reward mechanics and
    lifecycle current, but the target remains DRY_RUN/READ_ONLY and its actual earning
    action stays explicit-approval only.
    """

    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["extended_current_status_count"] = 0
    if not _is_fresh(now=current):
        _refresh_status_counts(result)
        return result

    for target in result.get("targets", []):
        if not isinstance(target, dict):
            continue
        slug = str(target.get("slug") or "")
        approval_state = EXTENDED_APPROVAL_STATES.get(slug)
        if approval_state is None:
            continue

        # Never relax a Terms/lifecycle/reward hard block established elsewhere.
        if (
            target.get("status") == "UNVERIFIED"
            or target.get("reward_acquisition_state") == "BLOCKED_UNVERIFIED"
            or target.get("program_lifecycle_status") in {"CONFLICT", "UNVERIFIED"}
            or target.get("api_reward_eligibility") == "UNVERIFIED"
        ):
            continue

        target.update(
            {
                "api_reward_eligibility": "CONFIRMED",
                "reward_evidence_source": EXTENDED_POINTS_SOURCE,
                "reward_rule_verified_at": EXTENDED_VERIFIED_AT,
                "reward_evidence_note": (
                    "Current official Extended documentation identifies organic trading and vault/liquidity "
                    "provision as points-earning categories, with points accruing on the Starknet version."
                ),
                "program_lifecycle_status": "ACTIVE",
                "program_lifecycle_sources": [
                    EXTENDED_POINTS_SOURCE,
                    EXTENDED_MIGRATION_SOURCE,
                    EXTENDED_REFERRAL_SOURCE,
                ],
                "program_lifecycle_verified_at": EXTENDED_VERIFIED_AT,
                "program_lifecycle_note": (
                    "Current official Points, Starknet migration and recently updated referral materials "
                    "continue to describe the Extended points system as in use on Starknet."
                ),
                "japan_legal_status": (
                    "JAPAN_NOT_IN_CURRENT_RESTRICTED_LIST_REVERIFY_ACCOUNT_TERMS_BEFORE_EXECUTION"
                ),
                "current_terms_sources": [EXTENDED_RESTRICTED_SOURCE, EXTENDED_TERMS_SOURCE],
                "current_evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "current_evidence_source": EXTENDED_POINTS_SOURCE,
                "current_evidence_checked_at": EXTENDED_VERIFIED_AT,
                "current_evidence_expires_at": _verification_expires_at(),
                "reward_acquisition_state": approval_state,
                "automation_permitted": False,
                "blocked_reason": (
                    "Current reward mechanics are verified, but LIVE earning requires financial/signing or "
                    "asset-movement approval. No economic action is authorized by this status refresh."
                ),
            }
        )
        result["extended_current_status_count"] += 1

    _refresh_status_counts(result)
    return result


def _refresh_counts(report: dict[str, Any]) -> None:
    actions = [item for item in report.get("actions", []) if isinstance(item, dict)]
    additional_paths = [
        item for item in report.get("additional_approval_paths", []) if isinstance(item, dict)
    ]
    primary_approval_required_count = sum(
        action.get("acquisition_state") in APPROVAL_STATES for action in actions
    )
    additional_approval_required_count = sum(
        path.get("acquisition_state") in APPROVAL_STATES for path in additional_paths
    )
    report["primary_approval_required_count"] = primary_approval_required_count
    report["additional_approval_required_count"] = additional_approval_required_count
    report["approval_required_count"] = (
        primary_approval_required_count + additional_approval_required_count
    )
    report["reverify_required_count"] = sum(
        action.get("acquisition_state") == "REVERIFY_REQUIRED" for action in actions
    )
    report["blocked_unverified_count"] = sum(
        action.get("acquisition_state") == "BLOCKED_UNVERIFIED" for action in actions
    )
    report["verified_gated_action_count"] = sum(
        action.get("evidence_status") == "PRIMARY_VERIFIED_CURRENT" for action in actions
    )


def _promote(
    report: dict[str, Any],
    *,
    slug: str,
    expected_approval_state: str,
    fields: dict[str, Any],
    now: datetime,
) -> bool:
    if not _is_fresh(now=now):
        return False

    expires = _verification_expires_at()
    for action in report.get("actions", []):
        if not isinstance(action, dict) or action.get("slug") != slug:
            continue
        # A generic approval state may already be produced from the now-current public
        # status (notably READ_ONLY liquidity). Enrich that state, but never override
        # a harder block or a different approval category.
        if action.get("acquisition_state") not in {"REVERIFY_REQUIRED", expected_approval_state}:
            return False
        action.update(
            {
                **fields,
                "verified_at": EXTENDED_VERIFIED_AT,
                "evidence_checked_at": EXTENDED_VERIFIED_AT,
                "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "verification_expires_at": expires,
                "action_taken": "NONE",
                "auto_executed": False,
                "points_delta": None,
            }
        )
        return True
    return False


def apply_extended_current_evidence(
    report: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Promote current Extended earning paths into approval queues only.

    This overlay never trades, deposits, withdraws, transfers assets, signs a wallet
    message or transaction, approves a token, bridges assets, or claims a reward.
    """

    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["extended_current_promotion_count"] = 0

    common_sources = [
        EXTENDED_POINTS_SOURCE,
        EXTENDED_MIGRATION_SOURCE,
        EXTENDED_RESTRICTED_SOURCE,
        EXTENDED_TERMS_SOURCE,
    ]

    if _promote(
        result,
        slug="extended-trading",
        expected_approval_state="APPROVAL_REQUIRED_FINANCIAL",
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_wallet_signature": True,
            "requires_real_order": True,
            "requires_asset_move": False,
            "authentication_recheck_required": True,
            "evidence_source": EXTENDED_POINTS_SOURCE,
            "evidence_sources": [*common_sources, EXTENDED_API_SOURCE, EXTENDED_REFERRAL_SOURCE],
            "source_coverage": "CURRENT_PRIMARY_OFFICIAL_EVIDENCE_WITH_EXTERNAL_CORROBORATION_CHECKED_SEPARATELY",
            "evidence_note": (
                "Current official Extended Points documentation keeps Season 1 in the active documentation tree, "
                "states that up to 1.2M points are distributed weekly on Tuesdays, and identifies organic trading "
                "as a points-earning category. The official Starknet migration guide says points accrue only on "
                "the Starknet version after migration, while current API documentation exposes the live Starknet "
                "Mainnet API and points endpoints. A recently updated official referral page still describes "
                "referrers earning a percentage of points generated by referrals, supporting that the points "
                "system remains in use. This verifies the reward path only; it does not authorize a real trade."
            ),
            "program_lifecycle_status": "ACTIVE_ON_STARKNET_PRIMARY_DOCS_CURRENT",
            "terms_status": (
                "JAPAN_NOT_IN_CURRENT_RESTRICTED_TERRITORY_LIST_REVERIFY_ACCOUNT_TERMS_API_KEYS_"
                "SIGNING_AND_LIVE_POINTS_PARAMETERS_BEFORE_EXECUTION"
            ),
            "known_cost_or_risk": (
                "Earning requires genuine trading on Extended. Real orders create trading fees, spread/slippage, "
                "funding, margin/liquidation and directional PnL risk. Current Terms prohibit unprovided automated "
                "access methods and restriction evasion; only Extended-provided interfaces/APIs may be considered, "
                "subject to current account eligibility. API/private actions require credentials/signing, and points "
                "have no verified fixed cash value, so there is no guaranteed positive reward-per-dollar."
            ),
            "missing_approval": (
                "Current account-specific eligibility and Terms acceptance; confirmation that the user is not a "
                "Restricted Person and is accessing from an allowed jurisdiction; exact Extended-provided API/UI "
                "authentication, API-key/Stark-key/private-signing flow; current points epoch/weights and fees; plus "
                "explicit market, side, maximum notional, leverage, fee/funding budget and maximum acceptable loss."
            ),
            "next_action": (
                "Immediately before any economic action, re-open the current Points, Restricted Countries and Terms "
                "pages and the authenticated account/API settings, confirm the live points epoch and exact signing "
                "requirements, then prepare a capped genuine-trading plan for explicit approval only. Do not place "
                "a real order, deposit, withdraw, bridge, approve tokens, sign a wallet/private-key action, self-trade, "
                "wash trade, manufacture volume or evade geographic/bot controls automatically."
            ),
        },
    ):
        result["extended_current_promotion_count"] += 1

    if _promote(
        result,
        slug="extended-liquidity",
        expected_approval_state="APPROVAL_REQUIRED_ASSET_MOVE",
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_wallet_signature": True,
            "requires_real_order": False,
            "requires_asset_move": True,
            "authentication_recheck_required": True,
            "evidence_source": EXTENDED_POINTS_SOURCE,
            "evidence_sources": [*common_sources, EXTENDED_VAULT_SOURCE, EXTENDED_REFERRAL_SOURCE],
            "source_coverage": "CURRENT_PRIMARY_OFFICIAL_EVIDENCE_WITH_EXTERNAL_CORROBORATION_CHECKED_SEPARATELY",
            "evidence_note": (
                "Current official Extended Points documentation identifies providing liquidity, including depositing "
                "funds into the vault, as a points-earning category. The current Vault documentation describes USDC "
                "deposits receiving XVS, a 24-hour lock per deposit, pro-rata position closing on withdrawal and active "
                "market-making/liquidation strategies. The migration guide says points accrue on Starknet, and a "
                "recently updated official referral page continues to reference generated points. This verifies an "
                "asset-movement earning path only; no deposit or signing action is authorized."
            ),
            "program_lifecycle_status": "ACTIVE_ON_STARKNET_PRIMARY_DOCS_CURRENT",
            "terms_status": (
                "JAPAN_NOT_IN_CURRENT_RESTRICTED_TERRITORY_LIST_REVERIFY_ACCOUNT_TERMS_WALLET_SIGNING_"
                "VAULT_CAP_LOCK_WITHDRAWAL_AND_LIVE_POINTS_PARAMETERS_BEFORE_EXECUTION"
            ),
            "known_cost_or_risk": (
                "Qualification requires moving USDC into the Extended Vault. The current docs state that XVS is "
                "used by an active market-making/liquidation strategy, each deposit has a 24-hour lock, withdrawals "
                "can bear price impact from closing the vault's positions, and XVS used as collateral can be affected "
                "by trading losses/liquidation. Additional risks include smart-contract/platform, stablecoin, "
                "liquidity/withdrawal, signing and opportunity-cost risk. Points and vault yield are not guaranteed "
                "to offset losses."
            ),
            "missing_approval": (
                "Current account-specific eligibility and Terms acceptance; current wallet/authentication and exact "
                "transaction/signing flow; live vault availability, XVS price/cap, lock, withdrawal and fee mechanics; "
                "current points epoch/weights; plus explicit USDC allocation amount, maximum acceptable loss and "
                "liquidity/withdrawal tolerance."
            ),
            "next_action": (
                "Immediately before any economic action, re-open the current Points, Vault, Restricted Countries and "
                "Terms pages and authenticated vault parameters, confirm the exact USDC-to-XVS deposit/signing and "
                "withdrawal flow, then prepare a capped allocation for explicit approval only. Do not deposit, "
                "withdraw, bridge, approve tokens, sign a wallet/private-key action or move assets automatically."
            ),
        },
    ):
        result["extended_current_promotion_count"] += 1

    _refresh_counts(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh current Extended reward evidence into explicit approval queues"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    updated = apply_extended_current_evidence(report)
    args.output.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "extended_current_promotion_count": updated.get(
                    "extended_current_promotion_count", 0
                ),
                "approval_required_count": updated.get("approval_required_count"),
                "reverify_required_count": updated.get("reverify_required_count"),
                "financial_actions_executed": updated.get("financial_actions_executed"),
                "asset_transfers_executed": updated.get("asset_transfers_executed"),
                "wallet_signatures_executed": updated.get("wallet_signatures_executed"),
                "live_orders_executed": updated.get("live_orders_executed"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
