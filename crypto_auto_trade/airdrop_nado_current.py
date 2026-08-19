from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from crypto_auto_trade.airdrop_live_overrides import OVERRIDE_TTL_DAYS


NADO_VERIFIED_AT = "2026-08-19T05:28:53+00:00"
NADO_POINTS_SOURCE = "https://docs.nado.xyz/points/season-1"
NADO_NLP_SOURCE = "https://docs.nado.xyz/nlp"
NADO_API_SOURCE = "https://docs.nado.xyz/developer-resources/api/rate-limits"
NADO_LOCK_SOURCE = "https://docs.nado.xyz/developer-resources/api/gateway/queries/nlp-locked-balances"
APPROVAL_STATES = {"APPROVAL_REQUIRED_FINANCIAL", "APPROVAL_REQUIRED_ASSET_MOVE"}


def _is_fresh(*, now: datetime) -> bool:
    verified = datetime.fromisoformat(NADO_VERIFIED_AT).astimezone(UTC)
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


def _promote(
    report: dict[str, Any],
    *,
    slug: str,
    fields: dict[str, Any],
    now: datetime,
) -> bool:
    if not _is_fresh(now=now):
        return False

    expires = (
        datetime.fromisoformat(NADO_VERIFIED_AT).astimezone(UTC)
        + timedelta(days=OVERRIDE_TTL_DAYS)
    )
    for action in report.get("actions", []):
        if not isinstance(action, dict) or action.get("slug") != slug:
            continue
        if action.get("acquisition_state") != "REVERIFY_REQUIRED":
            return False
        action.update(
            {
                **fields,
                "verified_at": NADO_VERIFIED_AT,
                "evidence_checked_at": NADO_VERIFIED_AT,
                "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "verification_expires_at": expires.isoformat(),
                "action_taken": "NONE",
                "auto_executed": False,
                "points_delta": None,
            }
        )
        return True
    return False


def apply_nado_current_evidence(
    report: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Refresh current Nado approval metadata only; never execute an earning action."""

    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["nado_current_promotion_count"] = 0

    if _promote(
        result,
        slug="nado-trading",
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_real_order": True,
            "requires_asset_move": False,
            "authentication_recheck_required": True,
            "evidence_source": NADO_POINTS_SOURCE,
            "evidence_sources": [NADO_POINTS_SOURCE, NADO_API_SOURCE],
            "source_coverage": "CURRENT_PRIMARY_OFFICIAL_ONLY_NO_INDEPENDENT_EXPERT_SOURCE",
            "evidence_note": (
                "Current official Nado Season 1 documentation describes a recurring weekly points program "
                "where genuine trading, market making, liquidations and other system-supporting trading "
                "activity can earn points. It explicitly excludes non-organic behavior including wash trading "
                "and self-matching. Current official API documentation also exposes production trading endpoints "
                "and rate limits, but this refresh does not treat API availability as permission to trade without "
                "explicit financial approval."
            ),
            "terms_status": (
                "REVERIFY_CURRENT_RESTRICTED_TERRITORIES_TERMS_JAPAN_ACCOUNT_"
                "AUTHENTICATION_AND_LIVE_MARKET_PARAMETERS_BEFORE_EXECUTION"
            ),
            "known_cost_or_risk": (
                "Qualification requires genuine market activity. Real orders can incur fees, spread/slippage, "
                "funding, margin/liquidation and directional PnL risk, while points have no verified fixed cash "
                "value here. Wash trading, self-matching, Sybil activity, manufactured volume and manipulative "
                "behavior are not permitted and must not be used to pursue points."
            ),
            "missing_approval": (
                "Current Nado Terms/restricted-territory and Japan/account eligibility check; account/API "
                "authentication and any signing requirement; plus explicit market/product, maximum notional, "
                "leverage, fee/spread/funding budget and maximum acceptable loss."
            ),
            "next_action": (
                "Immediately before any economic action, re-open the current Nado Points and restricted-territory "
                "rules, confirm account/API eligibility and authentication, select a genuine market action and "
                "calculate a capped worst-case fee/funding/PnL loss plan for explicit approval only. Do not place "
                "real orders, deposit funds, sign a wallet message, self-match, wash trade or manufacture volume "
                "automatically."
            ),
        },
    ):
        result["nado_current_promotion_count"] += 1

    if _promote(
        result,
        slug="nado-nlp",
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_real_order": False,
            "requires_asset_move": True,
            "authentication_recheck_required": True,
            "evidence_source": NADO_POINTS_SOURCE,
            "evidence_sources": [NADO_POINTS_SOURCE, NADO_NLP_SOURCE, NADO_LOCK_SOURCE],
            "source_coverage": "CURRENT_PRIMARY_OFFICIAL_ONLY_NO_INDEPENDENT_EXPERT_SOURCE",
            "evidence_note": (
                "Current official Nado Season 1 documentation says NLP participants earn points from their "
                "average proportional share of the vault during each weekly epoch. Current NLP documentation "
                "describes USDT0 deposits being deployed into active liquidity strategies, and the current locked-"
                "balances documentation confirms a four-day post-mint lock before the corresponding NLP balance "
                "can be burned for withdrawal."
            ),
            "terms_status": (
                "REVERIFY_CURRENT_RESTRICTED_TERRITORIES_TERMS_JAPAN_ACCOUNT_AUTHENTICATION_"
                "VAULT_CAP_LOCK_WITHDRAWAL_FEES_AND_SIGNING_BEFORE_EXECUTION"
            ),
            "known_cost_or_risk": (
                "Earning through NLP requires moving and locking capital in a vault that deploys active liquidity. "
                "Risks include vault/strategy PnL, market/liquidation exposure, smart-contract/platform/oracle "
                "risk, the published post-mint withdrawal lock, withdrawal/sequencer fees, liquidity constraints "
                "and opportunity cost. Points and vault yield are not guaranteed to offset those risks."
            ),
            "missing_approval": (
                "Current Nado Terms/restricted-territory and Japan/account eligibility; account/wallet/API "
                "authentication and exact signing flow; live NLP vault availability/cap, lock, withdrawal and fee "
                "parameters; plus explicit USDT0 allocation amount, maximum acceptable loss and liquidity/"
                "withdrawal tolerance."
            ),
            "next_action": (
                "Immediately before any economic action, re-open the current Nado Points/NLP/restricted-territory "
                "rules and authenticated vault parameters, confirm the exact mint/deposit/signing and withdrawal "
                "flow, then prepare a capped USDT0 allocation for explicit approval only. Do not deposit, mint, "
                "bridge, approve tokens, sign, withdraw or move assets automatically."
            ),
        },
    ):
        result["nado_current_promotion_count"] += 1

    _refresh_counts(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh current Nado reward evidence into explicit approval queues"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    updated = apply_nado_current_evidence(report)
    args.output.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "nado_current_promotion_count": updated.get(
                    "nado_current_promotion_count", 0
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
