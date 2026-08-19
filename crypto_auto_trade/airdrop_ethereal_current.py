from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


ETHEREAL_VERIFIED_AT = "2026-08-19T06:15:38+00:00"
ETHEREAL_APP_SOURCE = "https://app.ethereal.trade/"
ETHEREAL_POINTS_SOURCE = "https://docs.ethereal.trade/points/ethereal-points"
ETHEREAL_BALANCE_REWARDS_SOURCE = "https://docs.ethereal.trade/trading/usde-balance-rewards"
TTL_DAYS = 7
APPROVAL_STATES = {"APPROVAL_REQUIRED_FINANCIAL", "APPROVAL_REQUIRED_ASSET_MOVE"}
ETHEREAL_SLUGS = {"ethereal-trading", "ethereal-margin"}


def _is_fresh(*, now: datetime) -> bool:
    verified = datetime.fromisoformat(ETHEREAL_VERIFIED_AT).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=TTL_DAYS)


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
    report["blocked_unverified_count"] = sum(
        action.get("acquisition_state") == "BLOCKED_UNVERIFIED" for action in actions
    )
    report["reverify_required_count"] = sum(
        action.get("acquisition_state") == "REVERIFY_REQUIRED" for action in actions
    )
    report["verified_gated_action_count"] = sum(
        action.get("evidence_status") == "PRIMARY_VERIFIED_CURRENT" for action in actions
    )


def apply_ethereal_current(
    report: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Fail closed on Ethereal's current close-only migration state.

    This function never deposits, withdraws, bridges, signs, trades, claims, or moves assets.
    It only prevents stale reward documentation from being treated as an executable earning path.
    """

    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["ethereal_current_block_count"] = 0

    if not _is_fresh(now=current):
        return result

    expires = (
        datetime.fromisoformat(ETHEREAL_VERIFIED_AT).astimezone(UTC)
        + timedelta(days=TTL_DAYS)
    ).isoformat()

    for action in result.get("actions", []):
        if not isinstance(action, dict) or action.get("slug") not in ETHEREAL_SLUGS:
            continue

        slug = str(action.get("slug"))
        if slug == "ethereal-trading":
            next_action = (
                "Re-verify the current Ethereal-to-Meridian migration and Meridian reward rules from "
                "current official sources. Only if a new/increased genuine trading path is explicitly "
                "available and reward-eligible should a capped plan be prepared for separate financial "
                "and signing approval. Do not place reduce-only/closing trades merely to farm rewards, "
                "do not open or increase exposure, and do not sign or move assets automatically."
            )
            risk = (
                "The current official Ethereal application says Perps are close-only and directs users "
                "to close positions and bridge to Meridian. Older reward documentation still describes "
                "authentic trading as points-earning, so using that older documentation to initiate new "
                "reward-seeking exposure would rely on a stale lifecycle assumption. Any migration or "
                "future Meridian trading can involve wallet signatures, bridge/asset-transfer risk, fees, "
                "funding, slippage, liquidation and directional PnL risk."
            )
        else:
            next_action = (
                "Re-verify whether Ethereal still accepts/credits new USDe margin for rewards during the "
                "close-only migration and obtain current official Meridian reward/migration rules. If a "
                "capital-allocation path is explicitly supported, record the exact deposit/bridge/signing "
                "flow, amount, fees, lock/withdrawal mechanics and maximum loss for separate approval. "
                "Do not deposit, approve tokens, bridge, migrate, sign, withdraw or move assets automatically."
            )
            risk = (
                "Current Ethereal reward documentation still says USDe balances earn rewards, while the "
                "current official application is close-only and tells users to move funds to Meridian. "
                "That lifecycle conflict means a new Ethereal margin allocation is not treated as a "
                "currently verified acquisition path. Depositing or migrating would involve capital, "
                "wallet approval/signing, bridge/smart-contract/platform, stablecoin, fee, liquidity and "
                "withdrawal/opportunity-cost risk."
            )

        action.update(
            {
                "acquisition_state": "BLOCKED_UNVERIFIED",
                "automation_permitted": False,
                "requires_user_approval": False,
                "requires_funds": False,
                "requires_wallet_signature": False,
                "requires_real_order": False,
                "requires_asset_move": False,
                "authentication_recheck_required": True,
                "verified_at": ETHEREAL_VERIFIED_AT,
                "evidence_checked_at": ETHEREAL_VERIFIED_AT,
                "evidence_source": ETHEREAL_APP_SOURCE,
                "evidence_sources": [
                    ETHEREAL_APP_SOURCE,
                    ETHEREAL_POINTS_SOURCE,
                    ETHEREAL_BALANCE_REWARDS_SOURCE,
                ],
                "evidence_status": "PRIMARY_CURRENT_LIFECYCLE_CONFLICT_FAIL_CLOSED",
                "verification_expires_at": expires,
                "program_lifecycle_status": "CLOSE_ONLY_MIGRATING_TO_MERIDIAN",
                "terms_status": (
                    "REVERIFY_CURRENT_MERIDIAN_MIGRATION_REWARD_TERMS_JURISDICTION_"
                    "ACCOUNT_ELIGIBILITY_AND_SIGNING_BEFORE_ANY_ECONOMIC_ACTION"
                ),
                "evidence_note": (
                    "Current official Ethereal application states that Ethereal Perps are close-only, "
                    "instructs users to close positions and bridge to Meridian on Robinhood Chain, and "
                    "says Ethereal is becoming Meridian. Existing official Ethereal reward docs still "
                    "describe authentic trading and USDe margin balances as reward-earning. Because the "
                    "live application lifecycle and older reward docs do not establish a current new-"
                    "acquisition path during migration, the agent fails closed instead of inferring that "
                    "new trading or new margin deposits remain reward-eligible."
                ),
                "known_cost_or_risk": risk,
                "missing_approval": (
                    "Fresh official Meridian migration/reward rules that resolve whether this specific "
                    "earning path is currently open, plus current jurisdiction/account eligibility and "
                    "the exact authenticated/signing/asset-flow requirements. If an economic path is later "
                    "verified, explicit amount/notional, fee/funding/bridge budget, liquidity tolerance and "
                    "maximum acceptable loss are also required before execution."
                ),
                "next_action": next_action,
                "reason": (
                    "Current live-product migration evidence conflicts with the older Ethereal reward "
                    "lifecycle assumed by the base registry; fail closed until current primary sources "
                    "resolve the acquisition path."
                ),
                "action_taken": "NONE",
                "auto_executed": False,
                "points_delta": None,
            }
        )
        result["ethereal_current_block_count"] += 1

    _refresh_counts(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail closed on current Ethereal close-only migration evidence"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    updated = apply_ethereal_current(report)
    args.output.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "ethereal_current_block_count": updated.get("ethereal_current_block_count", 0),
                "approval_required_count": updated.get("approval_required_count"),
                "blocked_unverified_count": updated.get("blocked_unverified_count"),
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
