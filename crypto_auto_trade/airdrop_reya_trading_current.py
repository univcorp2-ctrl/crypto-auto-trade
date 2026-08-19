from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


REYA_TRADING_VERIFIED_AT = "2026-08-19T13:26:53+00:00"
REYA_RCP_SOURCE = "https://docs.reya.xyz/reya-token/reya-chain-points-faqs"
REYA_API_SOURCE = "https://docs.reya.xyz/technical-docs/reya-dex-rest-api-v2"
REYA_SITE_SOURCE = "https://reya.xyz/"
TTL_DAYS = 7
APPROVAL_STATES = {"APPROVAL_REQUIRED_FINANCIAL", "APPROVAL_REQUIRED_ASSET_MOVE"}


def _is_fresh(*, now: datetime) -> bool:
    verified = datetime.fromisoformat(REYA_TRADING_VERIFIED_AT).astimezone(UTC)
    current = now.astimezone(UTC)
    return verified <= current <= verified + timedelta(days=TTL_DAYS)


def _refresh_counts(report: dict[str, Any]) -> None:
    actions = [item for item in report.get("actions", []) if isinstance(item, dict)]
    additional_paths = [
        item for item in report.get("additional_approval_paths", []) if isinstance(item, dict)
    ]
    primary = sum(item.get("acquisition_state") in APPROVAL_STATES for item in actions)
    additional = sum(
        item.get("acquisition_state") in APPROVAL_STATES for item in additional_paths
    )
    report["primary_approval_required_count"] = primary
    report["additional_approval_required_count"] = additional
    report["approval_required_count"] = primary + additional
    report["blocked_unverified_count"] = sum(
        item.get("acquisition_state") == "BLOCKED_UNVERIFIED" for item in actions
    )
    report["reverify_required_count"] = sum(
        item.get("acquisition_state") == "REVERIFY_REQUIRED" for item in actions
    )
    report["verified_gated_action_count"] = sum(
        item.get("evidence_status") == "PRIMARY_VERIFIED_CURRENT" for item in actions
    )


def _expire_owned_overlay(report: dict[str, Any]) -> bool:
    for action in report.get("actions", []):
        if not isinstance(action, dict) or action.get("slug") != "reya-trading":
            continue
        if action.get("verified_at") != REYA_TRADING_VERIFIED_AT:
            return False
        if action.get("acquisition_state") != "APPROVAL_REQUIRED_FINANCIAL":
            return False
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
                    "REVERIFY_CURRENT_RCP_LIFECYCLE_TERMS_JURISDICTION_ACCOUNT_API_AND_SIGNING"
                ),
                "next_action": (
                    "Re-verify current Reya RCP trading mechanics, live exchange lifecycle, Terms/jurisdiction, "
                    "account eligibility, API authentication and wallet-signing requirements from current "
                    "primary sources before preparing any acquisition plan."
                ),
                "reason": (
                    "The Reya trading current-evidence overlay expired; fail closed until current primary "
                    "sources are re-verified."
                ),
                "action_taken": "NONE",
                "auto_executed": False,
            }
        )
        return True
    return False


def apply_reya_trading_current(
    report: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Promote current Reya trading evidence into approval only; never trade or sign."""

    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["reya_trading_current_promotion_count"] = 0

    if not _is_fresh(now=current):
        if _expire_owned_overlay(result):
            _refresh_counts(result)
        return result

    expires = (
        datetime.fromisoformat(REYA_TRADING_VERIFIED_AT).astimezone(UTC)
        + timedelta(days=TTL_DAYS)
    ).isoformat()

    for action in result.get("actions", []):
        if not isinstance(action, dict) or action.get("slug") != "reya-trading":
            continue
        if action.get("acquisition_state") != "REVERIFY_REQUIRED":
            break

        action.update(
            {
                "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
                "requires_user_approval": True,
                "requires_funds": True,
                "requires_wallet_signature": True,
                "requires_real_order": True,
                "requires_asset_move": False,
                "authentication_recheck_required": True,
                "verified_at": REYA_TRADING_VERIFIED_AT,
                "evidence_checked_at": REYA_TRADING_VERIFIED_AT,
                "evidence_source": REYA_RCP_SOURCE,
                "evidence_sources": [REYA_RCP_SOURCE, REYA_API_SOURCE, REYA_SITE_SOURCE],
                "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "verification_expires_at": expires,
                "source_coverage": "CURRENT_PRIMARY_OFFICIAL_REWARD_API_AND_LIVE_PRODUCT_SURFACES",
                "evidence_basis": "PRIMARY_DOCS_CHANNEL_NEUTRAL_INFERENCE_FOR_API_TRADES",
                "program_lifecycle_status": "ACTIVE_TRADING_SURFACE_AND_RCP_TRADING_TRACK_CURRENT",
                "evidence_note": (
                    "Current official Reya Chain Points FAQs state that Trading is an active RCP track and "
                    "that users earn RCP by trading any supported market on Reya. Reya's current official "
                    "site continues to expose live perpetual trading, and the current REST API v2 provides "
                    "production order entry for the same exchange. Private API actions require wallet "
                    "signatures. The reward rule is channel-neutral rather than an explicit sentence that "
                    "every API-originated trade earns RCP, so API eligibility is treated as a primary-docs "
                    "inference and is sufficient only for an approval queue, never automatic execution."
                ),
                "terms_status": (
                    "REVERIFY_CURRENT_REYA_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_API_AUTHENTICATION_"
                    "WALLET_SIGNING_AND_LIVE_RCP_PARAMETERS_BEFORE_EXECUTION"
                ),
                "known_cost_or_risk": (
                    "Earning requires genuine trading and therefore real economic exposure. Reya's current "
                    "site says trading uses a self-custody wallet and margin; real perpetual orders can incur "
                    "spread/slippage, funding, margin/liquidation and directional PnL risk even when visible "
                    "fees are low. Private API order actions require wallet signatures. RCP is non-transferable "
                    "and its eventual airdrop value is not fixed, so no positive reward-per-dollar or expected "
                    "profit is assumed."
                ),
                "missing_approval": (
                    "Current Reya Terms/jurisdiction and account eligibility; authenticated account/API state "
                    "and wallet-signing method; live RCP weighting/market eligibility and current trading-cost "
                    "parameters; plus explicit market, side, maximum notional, leverage, fee/spread/funding "
                    "budget and maximum acceptable loss. Any deposit, bridge, token approval or wallet "
                    "signature requires separate explicit approval and is not authorized by this queue entry."
                ),
                "next_action": (
                    "Immediately before any economic action, re-open the current RCP FAQ, Reya Terms/account "
                    "eligibility and live trading/API authentication surfaces, confirm the supported market "
                    "and current RCP treatment, then calculate a capped genuine-trading plan for explicit "
                    "financial/signing approval only. Do not deposit, withdraw, bridge, approve tokens, sign a "
                    "wallet message or transaction, submit a real order, self-trade, wash trade, manufacture "
                    "volume or evade regional/anti-bot controls automatically."
                ),
                "reason": (
                    "Fresh current official evidence supports the Reya trading reward path, but the qualifying "
                    "action requires real trading and wallet signing, so it belongs only in explicit approval."
                ),
                "action_taken": "NONE",
                "auto_executed": False,
                "points_delta": None,
            }
        )
        result["reya_trading_current_promotion_count"] = 1
        break

    _refresh_counts(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh current Reya trading/RCP evidence into the gated approval queue"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    updated = apply_reya_trading_current(report)
    args.output.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "reya_trading_current_promotion_count": updated.get(
                    "reya_trading_current_promotion_count", 0
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
