from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_acquisition import (
    DEFAULT_ACQUISITION_OUTPUT,
    build_acquisition_report,
    save_acquisition_report,
)
from crypto_auto_trade.airdrop_agents import (
    DEFAULT_OUTPUT as DEFAULT_STATUS_OUTPUT,
    TARGETS,
    AirdropTarget,
    dry_run_target,
    save_report,
    utc_now,
)
from crypto_auto_trade.airdrop_ethereal_current import (
    ETHEREAL_APP_SOURCE,
    ETHEREAL_BALANCE_REWARDS_SOURCE,
    ETHEREAL_POINTS_SOURCE,
    ETHEREAL_SLUGS,
    ETHEREAL_VERIFIED_AT,
    TTL_DAYS as ETHEREAL_TTL_DAYS,
)

# Decibel's current Terms of Use (last updated 2026-07-14), reviewed again on
# 2026-08-18 UTC, prohibit accessing the Services by automated means and also
# prohibit automated activity that circumvents Points Program limitations.
# The Terms define the covered Website broadly enough to include related sites,
# subdomains, applications and services. Any automated agent path therefore does
# not probe Decibel's program/API/rewards surfaces. It fails closed and leaves
# any financial/signing route for human/manual review + explicit approval.
DECIBEL_TERMS_SOURCE = "https://decibel.trade/terms-of-service"
DECIBEL_TERMS_VERIFIED_AT = "2026-08-18T23:19:02+00:00"
TERMS_AUTOMATION_BLOCKED_SLUGS = frozenset({"decibel-trading", "decibel-liquidity"})
TERMS_AUTOMATION_BLOCK_REASON = (
    "Current Decibel Terms prohibit access to the Services by automated means. "
    "Automated HTTP probing and automated reward acquisition are therefore disabled for this target. "
    "Use a human/manual current-terms and account-eligibility review before any separately approved financial action."
)

ETHEREAL_CURRENT_BLOCK_REASON = (
    "Current official Ethereal app lifecycle is close-only and migrating to Meridian while "
    "older official Ethereal reward pages still describe trading and USDe margin as reward-earning. "
    "Do not treat the older reward pages as a current acquisition authorization."
)
ETHEREAL_EXPIRED_BLOCK_REASON = (
    "The last verified Ethereal close-only/migration evidence has expired. Re-verify the current "
    "Ethereal/Meridian lifecycle and reward rules before treating trading or margin as an available "
    "reward-acquisition path."
)


def _evaluate_target(
    target: AirdropTarget, *, probe_network: bool = True
) -> dict[str, object]:
    if target.slug not in TERMS_AUTOMATION_BLOCKED_SLUGS:
        return dry_run_target(target, probe_network=probe_network)

    # Intentionally do not make an HTTP request to Decibel here, regardless of
    # whether the caller requested network probes for other targets.
    result = dry_run_target(target, probe_network=False)
    result.update(
        {
            "status": "UNVERIFIED",
            "program_probe": {
                "url": target.program_url,
                "ok": None,
                "status_code": None,
                "error": "skipped: current Terms prohibit automated access",
            },
            "api_probe": {
                "url": target.api_url,
                "ok": None,
                "status_code": None,
                "error": "skipped: current Terms prohibit automated access",
            },
            "blocked_reason": TERMS_AUTOMATION_BLOCK_REASON,
            "terms_automation_status": "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED",
            "terms_evidence_source": DECIBEL_TERMS_SOURCE,
            "terms_verified_at": DECIBEL_TERMS_VERIFIED_AT,
        }
    )
    return result


def _apply_ethereal_guard_to_status(
    report: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Propagate Ethereal's current lifecycle conflict to the public status report.

    This is status-only and never deposits, bridges, signs, trades, claims, or moves
    assets. If the evidence TTL expires, the status still fails closed as UNVERIFIED
    until a fresh primary-source lifecycle check replaces it.
    """

    current = (now or datetime.now(UTC)).astimezone(UTC)
    verified = datetime.fromisoformat(ETHEREAL_VERIFIED_AT).astimezone(UTC)
    fresh = verified <= current <= verified + timedelta(days=ETHEREAL_TTL_DAYS)
    blocked_count = 0

    for target in report.get("targets", []):
        if not isinstance(target, dict) or target.get("slug") not in ETHEREAL_SLUGS:
            continue

        target.update(
            {
                "status": "UNVERIFIED",
                "blocked_reason": (
                    ETHEREAL_CURRENT_BLOCK_REASON if fresh else ETHEREAL_EXPIRED_BLOCK_REASON
                ),
                "program_lifecycle_status": (
                    "CLOSE_ONLY_MIGRATING_TO_MERIDIAN"
                    if fresh
                    else "REVERIFY_REQUIRED_CURRENT_ETHEREAL_MERIDIAN_LIFECYCLE"
                ),
                "program_lifecycle_sources": [
                    ETHEREAL_APP_SOURCE,
                    ETHEREAL_POINTS_SOURCE,
                    ETHEREAL_BALANCE_REWARDS_SOURCE,
                ],
                "current_evidence_status": (
                    "PRIMARY_CURRENT_LIFECYCLE_CONFLICT_FAIL_CLOSED"
                    if fresh
                    else "PRIMARY_EVIDENCE_EXPIRED_REVERIFY_FAIL_CLOSED"
                ),
                "current_evidence_source": ETHEREAL_APP_SOURCE,
                "current_evidence_checked_at": ETHEREAL_VERIFIED_AT,
                "reward_acquisition_state": "BLOCKED_UNVERIFIED",
            }
        )
        blocked_count += 1

    targets = [item for item in report.get("targets", []) if isinstance(item, dict)]
    report["ready_dry_run"] = sum(item.get("status") == "READY_DRY_RUN" for item in targets)
    report["read_only"] = sum(item.get("status") == "READ_ONLY" for item in targets)
    report["unverified"] = sum(item.get("status") == "UNVERIFIED" for item in targets)
    report["ethereal_current_block_count"] = blocked_count
    return report


def run_terms_safe_status(*, probe_network: bool = True) -> dict[str, object]:
    targets = list(TARGETS)
    worker_count = min(12, len(targets))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(
            executor.map(
                lambda target: _evaluate_target(target, probe_network=probe_network),
                targets,
            )
        )

    report: dict[str, Any] = {
        "generated_at": utc_now(),
        "mode": "DRY_RUN",
        "live_approved": False,
        "target_count": len(results),
        "ready_dry_run": sum(item["status"] == "READY_DRY_RUN" for item in results),
        "read_only": sum(item["status"] == "READ_ONLY" for item in results),
        "unverified": sum(item["status"] == "UNVERIFIED" for item in results),
        "terms_automation_blocked_count": sum(
            item.get("terms_automation_status") == "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED"
            for item in results
        ),
        "targets": results,
    }
    return _apply_ethereal_guard_to_status(report)


def _is_approval_state(state: object) -> bool:
    return state in {"APPROVAL_REQUIRED_FINANCIAL", "APPROVAL_REQUIRED_ASSET_MOVE"}


def _apply_terms_guard_to_acquisition(report: dict[str, Any]) -> dict[str, Any]:
    for action in report.get("actions", []):
        if not isinstance(action, dict) or action.get("slug") not in TERMS_AUTOMATION_BLOCKED_SLUGS:
            continue
        action.update(
            {
                "acquisition_state": "BLOCKED_UNVERIFIED",
                "automation_permitted": False,
                "terms_status": "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED",
                "terms_evidence_source": DECIBEL_TERMS_SOURCE,
                "terms_verified_at": DECIBEL_TERMS_VERIFIED_AT,
                "next_action": (
                    "Perform a human/manual current Decibel Terms, campaign-rules and account-eligibility review. "
                    "If a genuine financial or signing action remains permitted, record its exact market/action, "
                    "maximum notional or asset amount, fees/network cost, leverage/lock/withdrawal risk and required "
                    "signature, then keep it in explicit approval. Do not use automated access to Decibel Services."
                ),
                "reason": TERMS_AUTOMATION_BLOCK_REASON,
            }
        )

    actions = [action for action in report.get("actions", []) if isinstance(action, dict)]
    additional_paths = [
        path for path in report.get("additional_approval_paths", []) if isinstance(path, dict)
    ]
    primary_approval_required_count = sum(
        _is_approval_state(action.get("acquisition_state")) for action in actions
    )
    additional_approval_required_count = sum(
        _is_approval_state(path.get("acquisition_state")) for path in additional_paths
    )

    report["blocked_unverified_count"] = sum(
        action.get("acquisition_state") == "BLOCKED_UNVERIFIED" for action in actions
    )
    report["reverify_required_count"] = sum(
        action.get("acquisition_state") == "REVERIFY_REQUIRED" for action in actions
    )
    report["primary_approval_required_count"] = primary_approval_required_count
    report["additional_approval_required_count"] = additional_approval_required_count
    report["approval_required_count"] = (
        primary_approval_required_count + additional_approval_required_count
    )
    report["terms_automation_blocked_count"] = len(TERMS_AUTOMATION_BLOCKED_SLUGS)
    report["terms_automation_guard_source"] = DECIBEL_TERMS_SOURCE
    report["terms_automation_guard_verified_at"] = DECIBEL_TERMS_VERIFIED_AT
    return report


def run_terms_safe_acquisition_cycle(
    *,
    status_output: Path = DEFAULT_STATUS_OUTPUT,
    acquisition_output: Path = DEFAULT_ACQUISITION_OUTPUT,
) -> dict[str, Any]:
    status_report = run_terms_safe_status()
    save_report(status_report, status_output)
    acquisition_report = build_acquisition_report(status_report)
    acquisition_report = _apply_terms_guard_to_acquisition(acquisition_report)
    save_acquisition_report(acquisition_report, acquisition_output)
    return acquisition_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Airdrop acquisition cycle while honoring target-specific automated-access terms"
    )
    parser.add_argument("--status-output", type=Path, default=DEFAULT_STATUS_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_ACQUISITION_OUTPUT)
    args = parser.parse_args()

    report = run_terms_safe_acquisition_cycle(
        status_output=args.status_output,
        acquisition_output=args.output,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "target_count": report.get("target_count"),
                "blocked_unverified_count": report.get("blocked_unverified_count"),
                "terms_automation_blocked_count": report.get("terms_automation_blocked_count"),
                "financial_actions_executed": report.get("financial_actions_executed"),
                "wallet_signatures_executed": report.get("wallet_signatures_executed"),
                "live_orders_executed": report.get("live_orders_executed"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
