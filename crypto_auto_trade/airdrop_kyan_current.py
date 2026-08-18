from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

KYAN_VERIFIED_AT = "2026-08-18T03:20:11+00:00"
KYAN_REWARD_SOURCE = "https://blog.kyan.blue/p/development-update-referrals-rewards-hub-and-more"
KYAN_BLOG_INDEX_SOURCE = "https://blog.kyan.blue/"
KYAN_MAIN_SITE_SOURCE = "https://www.kyan.blue/"
KYAN_MCP_SOURCE = "https://docs.kyan.blue/docs/mcp"
KYAN_ONE_CLICK_SOURCE = "https://docs.kyan.blue/reference/createsession"
TTL_DAYS = 7


def _fresh(now: datetime) -> bool:
    verified = datetime.fromisoformat(KYAN_VERIFIED_AT).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=TTL_DAYS)


def _refresh_acquisition_counts(report: dict[str, Any]) -> None:
    actions = [item for item in report.get("actions", []) if isinstance(item, dict)]
    additional_paths = report.get("additional_approval_paths", [])
    if not isinstance(additional_paths, list):
        additional_paths = []

    primary_approval_required_count = sum(
        bool(item.get("requires_user_approval")) for item in actions
    )
    additional_approval_required_count = sum(
        isinstance(path, dict) and bool(path.get("requires_user_approval", True))
        for path in additional_paths
    )

    report["verified_gated_action_count"] = sum(
        item.get("evidence_status") == "PRIMARY_VERIFIED_CURRENT" for item in actions
    )
    report["safe_auth_required_count"] = sum(
        item.get("acquisition_state") == "SAFE_ACTION_AUTH_REQUIRED" for item in actions
    )
    report["auto_executed_action_count"] = sum(
        bool(item.get("auto_executed")) for item in actions
    )
    report["primary_approval_required_count"] = primary_approval_required_count
    report["additional_approval_required_count"] = additional_approval_required_count
    report["approval_required_count"] = (
        primary_approval_required_count + additional_approval_required_count
    )
    report["blocked_unverified_count"] = sum(
        item.get("acquisition_state") == "BLOCKED_UNVERIFIED" for item in actions
    )
    report["reverify_required_count"] = sum(
        item.get("acquisition_state") == "REVERIFY_REQUIRED" for item in actions
    )
    report["discovery_only_count"] = sum(
        item.get("acquisition_state") == "DISCOVERY_ONLY" for item in actions
    )


def _expire_owned_overlay(
    status: dict[str, Any], acquisition: dict[str, Any]
) -> bool:
    """Fail closed only for metadata previously written by this exact overlay."""
    changed = False

    for target in status.get("targets", []):
        if not isinstance(target, dict) or target.get("slug") != "kyan":
            continue
        if target.get("program_lifecycle_verified_at") != KYAN_VERIFIED_AT:
            continue
        target.update(
            {
                "program_lifecycle_status": "REVERIFY",
                "program_lifecycle_sources": [],
                "program_lifecycle_verified_at": None,
                "program_lifecycle_note": (
                    "The Kyan public-current lifecycle evidence used by this overlay has expired. "
                    "Re-verify current primary sources before treating the program lifecycle as active."
                ),
            }
        )
        changed = True
        break

    for action in acquisition.get("actions", []):
        if not isinstance(action, dict) or action.get("slug") != "kyan":
            continue
        if action.get("verified_at") != KYAN_VERIFIED_AT:
            continue
        action.update(
            {
                "acquisition_state": "REVERIFY_REQUIRED",
                "requires_user_approval": False,
                "requires_funds": False,
                "requires_wallet_signature": False,
                "requires_real_order": False,
                "requires_asset_move": False,
                "authentication_recheck_required": False,
                "evidence_status": "EXPIRED_REVERIFY_REQUIRED",
                "program_lifecycle_status": "REVERIFY",
                "terms_status": (
                    "REVERIFY_CURRENT_KRYSTALS_LIFECYCLE_TERMS_JURISDICTION_ACCOUNT_API_KEY_AND_SIGNING"
                ),
                "next_action": (
                    "Re-verify Kyan's current Krystals earning mechanics, program lifecycle, "
                    "Terms/jurisdiction, account eligibility, API-key permissions and signing "
                    "requirements from current primary sources before preparing any acquisition plan."
                ),
                "reason": (
                    "The current-evidence overlay expired; no Kyan earning action is treated as "
                    "currently verified until primary-source re-verification is completed."
                ),
                "action_taken": "NONE",
                "auto_executed": False,
            }
        )
        changed = True
        break

    if changed:
        _refresh_acquisition_counts(acquisition)
    return changed


def apply_kyan_current(
    status_report: dict[str, Any],
    acquisition_report: dict[str, Any],
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Refresh Kyan public-current evidence only; never authorize or execute trading/signing."""
    current = now or datetime.now(UTC)
    status = copy.deepcopy(status_report)
    acquisition = copy.deepcopy(acquisition_report)

    if not _fresh(current):
        changed = _expire_owned_overlay(status, acquisition)
        return status, acquisition, changed

    expires = (
        datetime.fromisoformat(KYAN_VERIFIED_AT).astimezone(UTC)
        + timedelta(days=TTL_DAYS)
    ).isoformat()
    changed = False

    for target in status.get("targets", []):
        if not isinstance(target, dict) or target.get("slug") != "kyan":
            continue
        target.update(
            {
                "program_lifecycle_status": "ACTIVE",
                "program_lifecycle_sources": [
                    KYAN_REWARD_SOURCE,
                    KYAN_BLOG_INDEX_SOURCE,
                    KYAN_MAIN_SITE_SOURCE,
                    KYAN_MCP_SOURCE,
                ],
                "program_lifecycle_verified_at": KYAN_VERIFIED_AT,
                "program_lifecycle_note": (
                    "Current official Kyan surfaces still show mainnet live, a dedicated Rewards hub, "
                    "Krystals earned from users' own trading, and production-capable API/MCP access. "
                    "This verifies the public Krystals program lifecycle as active, but does not verify "
                    "account eligibility, jurisdiction/Terms, API-key permissions, signing setup, or "
                    "make any live trading action permissible."
                ),
            }
        )
        changed = True
        break

    for action in acquisition.get("actions", []):
        if not isinstance(action, dict) or action.get("slug") != "kyan":
            continue
        if action.get("acquisition_state") not in {
            "APPROVAL_REQUIRED_FINANCIAL",
            "REVERIFY_REQUIRED",
        }:
            continue

        sources = list(action.get("evidence_sources") or [])
        for source in [
            KYAN_REWARD_SOURCE,
            KYAN_BLOG_INDEX_SOURCE,
            KYAN_MAIN_SITE_SOURCE,
            KYAN_MCP_SOURCE,
            KYAN_ONE_CLICK_SOURCE,
        ]:
            if source not in sources:
                sources.append(source)

        action.update(
            {
                "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
                "requires_user_approval": True,
                "requires_funds": True,
                "requires_wallet_signature": True,
                "requires_real_order": True,
                "requires_asset_move": False,
                "authentication_recheck_required": True,
                "verified_at": KYAN_VERIFIED_AT,
                "evidence_checked_at": KYAN_VERIFIED_AT,
                "evidence_source": KYAN_REWARD_SOURCE,
                "evidence_sources": sources,
                "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "verification_expires_at": expires,
                "program_lifecycle_status": "ACTIVE",
                "evidence_note": (
                    "Current official Kyan public surfaces still show mainnet live and a dedicated "
                    "Rewards hub where users track Krystals; Kyan states users continue earning "
                    "Krystals from their own trading. Current official MCP/API documentation supports "
                    "production API calls on the same exchange. API-originated Krystals remain a "
                    "channel-neutral inference rather than an explicit per-API-trade promise."
                ),
                "reason": (
                    "Current primary sources support the Krystals program lifecycle and genuine "
                    "trading reward path, but earning requires financial exposure and signing."
                ),
                "terms_status": (
                    "KRYSTALS_LIFECYCLE_ACTIVE_REVERIFY_TERMS_JURISDICTION_ACCOUNT_API_KEY_AND_SIGNING"
                ),
                "known_cost_or_risk": (
                    "Qualification requires genuine derivatives trading. Real orders create fee, "
                    "spread/slippage, funding or option-premium, margin, liquidation and directional "
                    "PnL risk. Kyan's one-click trading session requires an initial EIP-712 wallet "
                    "signature, and account eligibility, current Terms/jurisdiction and Krystals "
                    "weights can change. The current public evidence does not establish positive "
                    "expected value or a fixed reward-per-dollar."
                ),
                "missing_approval": (
                    "Current Kyan Terms/jurisdiction and account eligibility; authenticated Rewards "
                    "hub/account Krystals status; API-key permissions; the EIP-712 one-click session "
                    "signing setup; and explicit market/product, maximum notional, leverage, "
                    "fee/premium/funding budget and maximum acceptable loss."
                ),
                "next_action": (
                    "In a supported authenticated Kyan session, perform read-only checks of the "
                    "Rewards hub, current Terms/account eligibility, API-key permissions and signing "
                    "requirements. If eligible, prepare a capped genuine-trading plan for explicit "
                    "financial/signing approval. Do not create/sign a session, submit a real order, "
                    "move assets, self-trade, wash trade or manufacture volume automatically."
                ),
                "action_taken": "NONE",
                "auto_executed": False,
            }
        )
        changed = True
        break

    if changed:
        _refresh_acquisition_counts(acquisition)
    return status, acquisition, changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh current Kyan Krystals lifecycle metadata safely."
    )
    parser.add_argument("--status-input", required=True)
    parser.add_argument("--status-output", required=True)
    parser.add_argument("--acquisition-input", required=True)
    parser.add_argument("--acquisition-output", required=True)
    args = parser.parse_args()

    status_path = Path(args.status_input)
    acquisition_path = Path(args.acquisition_input)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    updated_status, updated_acquisition, changed = apply_kyan_current(
        status, acquisition
    )

    Path(args.status_output).write_text(
        json.dumps(updated_status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.acquisition_output).write_text(
        json.dumps(updated_acquisition, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        {
            "kyan_current_applied": changed,
            "verified_at": KYAN_VERIFIED_AT,
            "financial_action_executed": False,
            "wallet_signature_executed": False,
            "live_order_executed": False,
        }
    )


if __name__ == "__main__":
    main()
