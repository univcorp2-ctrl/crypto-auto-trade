from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_live_overrides import (
    OVERRIDE_TTL_DAYS,
    STANDX_MAKER_EVIDENCE_SOURCE,
    STANDX_MAKER_LIVE_PARAMETERS,
    STANDX_MAKER_VERIFIED_AT,
)


APPROVAL_STATES = {"APPROVAL_REQUIRED_FINANCIAL", "APPROVAL_REQUIRED_ASSET_MOVE"}


def _verified_at_is_fresh(verified_at: str, *, now: datetime) -> bool:
    verified = datetime.fromisoformat(verified_at).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=OVERRIDE_TTL_DAYS)


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


def promote_current_verified_paths(
    report: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Promote only still-current primary-source overlays; never execute an action.

    The base acquisition registry and the live-parameter overlays intentionally use
    independent TTLs. A fresher overlay must be able to keep a target in the
    appropriate approval queue when the older base entry expires, otherwise the
    workflow falsely falls back to REVERIFY_REQUIRED despite newer primary-source
    evidence already being present.
    """

    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["current_evidence_promotion_count"] = 0

    if _verified_at_is_fresh(STANDX_MAKER_VERIFIED_AT, now=current):
        for action in result.get("actions", []):
            if not isinstance(action, dict) or action.get("slug") != "standx-maker":
                continue
            if action.get("acquisition_state") != "REVERIFY_REQUIRED":
                continue

            expires = (
                datetime.fromisoformat(STANDX_MAKER_VERIFIED_AT).astimezone(UTC)
                + timedelta(days=OVERRIDE_TTL_DAYS)
            )
            action.update(
                {
                    "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
                    "requires_user_approval": True,
                    "requires_funds": True,
                    "requires_real_order": True,
                    "requires_asset_move": False,
                    "verified_at": STANDX_MAKER_VERIFIED_AT,
                    "evidence_checked_at": STANDX_MAKER_VERIFIED_AT,
                    "evidence_source": STANDX_MAKER_EVIDENCE_SOURCE,
                    "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                    "verification_expires_at": expires.isoformat(),
                    "evidence_note": (
                        "Current official StandX Community Maker Yield documentation requires real executable "
                        "two-sided liquidity within 10 bps, at least 30 qualifying minutes per hour for the "
                        "standard tier, and daily reward settlement. Current per-pair unit sizes, caps, sessions "
                        "and hourly ceilings remain live parameters and must be rechecked before any economic action."
                    ),
                    "live_parameters": STANDX_MAKER_LIVE_PARAMETERS,
                    "terms_status": (
                        "REVERIFY_PERPS_USER_ELIGIBILITY_TERMS_AUTHENTICATION_"
                        "AND_LIVE_PAIR_PARAMETERS_BEFORE_EXECUTION"
                    ),
                    "known_cost_or_risk": (
                        "Qualifying quotes are real executable orders and can fill, creating directional exposure, "
                        "adverse selection, spread/slippage, funding, margin and liquidation risk. The daily reward "
                        "pool and per-pair parameters can change, so no fixed reward-per-dollar is assumed."
                    ),
                    "missing_approval": (
                        "Current StandX Terms/jurisdiction and account eligibility, authentication/signing method, "
                        "selected pair and current live unit size/cap/session/fee tier, plus explicit maximum notional, "
                        "quote distance, uptime window, fee/funding/adverse-selection budget and maximum acceptable loss."
                    ),
                    "next_action": (
                        "Immediately before any economic action, re-open the current StandX Community Maker Yield page "
                        "and Terms/account eligibility, select one pair, calculate capped worst-case fill/funding/"
                        "adverse-selection exposure, and prepare the plan for explicit approval only. Do not place, "
                        "cancel, maintain or replenish real maker orders automatically."
                    ),
                    "action_taken": "NONE",
                    "auto_executed": False,
                }
            )
            result["current_evidence_promotion_count"] += 1
            break

    _refresh_counts(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote fresh current primary-source overlays into the gated approval queue"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    updated = promote_current_verified_paths(report)
    args.output.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "current_evidence_promotion_count": updated.get(
                    "current_evidence_promotion_count", 0
                ),
                "approval_required_count": updated.get("approval_required_count"),
                "reverify_required_count": updated.get("reverify_required_count"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
