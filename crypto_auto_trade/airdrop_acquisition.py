from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_agents import DEFAULT_OUTPUT as DEFAULT_STATUS_OUTPUT
from crypto_auto_trade.airdrop_agents import run_all, save_report

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACQUISITION_OUTPUT = ROOT / "data" / "airdrop" / "acquisition-latest.json"

# Safe automatic acquisition adapters must satisfy ALL of these conditions:
# - no deposit / withdrawal / bridge / token approval / value transfer
# - no wallet signature or private-key access
# - no real order or economic exposure
# - explicitly permitted by current official program rules
# - deterministic proof that the action can earn the advertised reward
#
# No current Wave 1 target meets that standard. Keep this registry empty until an
# adapter is verified against current primary documentation and covered by tests.
SAFE_AUTO_ACTIONS: dict[str, dict[str, Any]] = {}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _classify_target(target: dict[str, Any]) -> dict[str, Any]:
    slug = str(target["slug"])
    status = str(target["status"])
    mode = str(target["mode"])
    wave = int(target["wave"])
    lifecycle = str(target.get("program_lifecycle_status") or "REVERIFY")
    reward_eligibility = str(target.get("api_reward_eligibility") or "REVERIFY")

    base = {
        "slug": slug,
        "name": target["name"],
        "wave": wave,
        "program_url": target["program_url"],
        "reward_unit": target["reward_unit"],
        "action_taken": "NONE",
        "auto_executed": False,
        "requires_user_approval": False,
        "requires_funds": False,
        "requires_wallet_signature": False,
        "points_delta": None,
    }

    # Hard-block explicit conflicts and explicit unverified reward mechanics.
    if status == "UNVERIFIED" or lifecycle in {"CONFLICT", "UNVERIFIED"} or reward_eligibility == "UNVERIFIED":
        return {
            **base,
            "acquisition_state": "BLOCKED_UNVERIFIED",
            "next_action": "Re-verify current reward mechanics and program lifecycle from official sources before any acquisition action.",
            "reason": target.get("blocked_reason") or "Reward eligibility or program lifecycle is not verified.",
        }

    if slug in SAFE_AUTO_ACTIONS:
        # Deliberately fail closed until an explicit adapter implementation is added.
        # A registry entry alone must never create a financial or signing side effect.
        return {
            **base,
            "acquisition_state": "SAFE_ADAPTER_NOT_IMPLEMENTED",
            "next_action": "Implement and test the verified non-financial adapter before enabling automatic execution.",
            "reason": "A safe-action specification exists, but executable code is intentionally not enabled yet.",
        }

    # Wave 1 is the first execution wave. Pacifica/Hibachi have verified mechanics,
    # but earning requires genuine exchange activity, so the cycle prepares rather
    # than silently submitting financial actions.
    if wave == 1 and slug in {"pacifica", "hibachi"}:
        return {
            **base,
            "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_wallet_signature": slug == "pacifica",
            "next_action": "Queue a capped genuine-trading plan for explicit approval; do not place orders automatically.",
            "reason": "Current official reward mechanics require genuine exchange activity; this creates economic exposure and can require signed/authenticated orders.",
        }

    if mode == "SCOUT":
        return {
            **base,
            "acquisition_state": "DISCOVERY_ONLY",
            "next_action": "Continue discovery and promote a candidate only after an exact qualifying action is verified.",
            "reason": "This adapter is a discovery source, not an earning executor.",
        }

    # Most Wave 2/3 adapters have not yet had current mechanics/lifecycle promoted
    # from REVERIFY. Keep them distinct from hard-blocked/conflicted Wave 1 targets.
    if lifecycle == "REVERIFY" or reward_eligibility == "REVERIFY":
        return {
            **base,
            "acquisition_state": "REVERIFY_REQUIRED",
            "next_action": "Verify current earning action, program lifecycle, Japan/Terms eligibility, costs and required authentication before implementing acquisition.",
            "reason": "This target is queued for current primary-source re-verification; it is not treated as a confirmed failure or confirmed earning path.",
        }

    if mode == "READ_ONLY":
        return {
            **base,
            "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
            "requires_user_approval": True,
            "requires_funds": True,
            "next_action": "Verify current reward rules, then prepare any deposit/stake/liquidity action for explicit approval.",
            "reason": "The configured target is read-only because earning may require asset movement or capital lock-up.",
        }

    return {
        **base,
        "acquisition_state": "REVERIFY_REQUIRED",
        "next_action": "Verify current earning action, Japan/Terms eligibility, costs and required authentication before implementing acquisition.",
        "reason": "No currently verified zero-value-transfer, no-signature acquisition adapter is implemented for this target.",
    }


def build_acquisition_report(status_report: dict[str, Any]) -> dict[str, Any]:
    actions = [_classify_target(target) for target in status_report.get("targets", [])]
    return {
        "generated_at": utc_now(),
        "mode": "ACQUISITION_GATED",
        "objective": "Execute only verified non-financial/no-signature reward actions automatically; queue financial or signing actions for approval.",
        "target_count": len(actions),
        "safe_auto_adapter_count": len(SAFE_AUTO_ACTIONS),
        "auto_executed_action_count": sum(bool(item["auto_executed"]) for item in actions),
        "approval_required_count": sum(bool(item["requires_user_approval"]) for item in actions),
        "blocked_unverified_count": sum(item["acquisition_state"] == "BLOCKED_UNVERIFIED" for item in actions),
        "reverify_required_count": sum(item["acquisition_state"] == "REVERIFY_REQUIRED" for item in actions),
        "discovery_only_count": sum(item["acquisition_state"] == "DISCOVERY_ONLY" for item in actions),
        "financial_actions_executed": 0,
        "asset_transfers_executed": 0,
        "wallet_signatures_executed": 0,
        "live_orders_executed": 0,
        "live_approved": False,
        "actions": actions,
    }


def save_acquisition_report(report: dict[str, Any], output: Path = DEFAULT_ACQUISITION_OUTPUT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def run_acquisition_cycle(*, probe_network: bool = True, status_output: Path = DEFAULT_STATUS_OUTPUT, acquisition_output: Path = DEFAULT_ACQUISITION_OUTPUT) -> dict[str, Any]:
    status_report = run_all(probe_network=probe_network)
    save_report(status_report, status_output)
    acquisition_report = build_acquisition_report(status_report)
    save_acquisition_report(acquisition_report, acquisition_output)
    return acquisition_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Gated airdrop acquisition cycle: auto-safe actions only, financial/signing actions queued for approval")
    parser.add_argument("--status-output", type=Path, default=DEFAULT_STATUS_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_ACQUISITION_OUTPUT)
    parser.add_argument("--no-network", action="store_true", help="Skip official-document reachability checks")
    args = parser.parse_args()
    report = run_acquisition_cycle(
        probe_network=not args.no_network,
        status_output=args.status_output,
        acquisition_output=args.output,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "mode": report["mode"],
                "output": str(args.output),
                "target_count": report["target_count"],
                "auto_executed_action_count": report["auto_executed_action_count"],
                "approval_required_count": report["approval_required_count"],
                "blocked_unverified_count": report["blocked_unverified_count"],
                "reverify_required_count": report["reverify_required_count"],
                "live_approved": report["live_approved"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
