from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
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

# Decibel's current Terms of Use (last updated 2026-07-14), reviewed again on
# 2026-08-18 UTC, prohibit accessing the Services by automated means and also
# prohibit automated activity that circumvents Points Program limitations.
# The Terms define the covered Website broadly enough to include related sites,
# subdomains, applications and services. The scheduled agent therefore does not
# automatically probe Decibel's program/API/rewards surfaces. It fails closed
# and leaves any financial/signing route for manual review + explicit approval.
DECIBEL_TERMS_SOURCE = "https://decibel.trade/terms-of-service"
DECIBEL_TERMS_VERIFIED_AT = "2026-08-18T23:19:02+00:00"
TERMS_AUTOMATION_BLOCKED_SLUGS = frozenset({"decibel-trading", "decibel-liquidity"})
TERMS_AUTOMATION_BLOCK_REASON = (
    "Current Decibel Terms prohibit access to the Services by automated means. "
    "Scheduled HTTP probing and automated reward acquisition are therefore disabled for this target. "
    "Use a human/manual current-terms and account-eligibility review before any separately approved financial action."
)


def _evaluate_target(target: AirdropTarget) -> dict[str, object]:
    if target.slug not in TERMS_AUTOMATION_BLOCKED_SLUGS:
        return dry_run_target(target, probe_network=True)

    # Intentionally do not make an HTTP request to Decibel here.
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


def run_terms_safe_status() -> dict[str, object]:
    targets = list(TARGETS)
    worker_count = min(12, len(targets))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(_evaluate_target, targets))

    return {
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

    report["blocked_unverified_count"] = sum(
        isinstance(action, dict) and action.get("acquisition_state") == "BLOCKED_UNVERIFIED"
        for action in report.get("actions", [])
    )
    report["reverify_required_count"] = sum(
        isinstance(action, dict) and action.get("acquisition_state") == "REVERIFY_REQUIRED"
        for action in report.get("actions", [])
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
