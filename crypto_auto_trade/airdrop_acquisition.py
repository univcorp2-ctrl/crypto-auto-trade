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
# No currently verified target meets that standard. Keep this registry empty until
# an adapter is verified against current primary documentation and covered by tests.
SAFE_AUTO_ACTIONS: dict[str, dict[str, Any]] = {}

# Current primary-source verifications that are strong enough to move an item out of
# REVERIFY_REQUIRED and into an explicit human approval queue. These entries do NOT
# authorize execution. They only record that the earning path is current and that
# the remaining blocker is financial/signing/legal approval.
CURRENT_EARNING_VERIFICATION: dict[str, dict[str, Any]] = {
    "standx-maker": {
        "state": "APPROVAL_REQUIRED_FINANCIAL",
        "verified_at": "2026-08-12",
        "sources": [
            "https://docs.standx.com/docs/standx-perps-solutions/community-maker-yield",
            "https://docs.standx.com/sip/sip-5a-community-maker-yield",
            "https://docs.standx.com/standx-api/standx-api",
            "https://docs.standx.com/standx-api/perps-http",
        ],
        "reason": "StandX Community Maker Yield is implemented and currently pays makers for real executable two-sided liquidity. The official Perps API supports programmatic order placement, and signed/authenticated order submission is required.",
        "next_action": "Prepare a capped two-sided ALO quoting plan inside the current 10 bps qualifying band and target at least 30 minutes of qualifying uptime per hour; do not submit live orders until explicit financial/legal approval.",
        "known_cost_risk": "Requires real perpetual-market orders and inventory exposure. Main risks are adverse selection, spread/funding movement, liquidation/margin risk, and operational API/signature risk. Reward pool size is variable.",
        "missing_approval": "Explicit approval for real perps exposure, capital/margin use, wallet/API signing, and Japan/Terms eligibility.",
        "requires_wallet_signature": True,
    },
    "standx-position": {
        "state": "APPROVAL_REQUIRED_FINANCIAL",
        "verified_at": "2026-08-12",
        "sources": [
            "https://docs.standx.com/sip/sip-2-position-yield",
            "https://docs.standx.com/blog/articles/sip-2-position-yield",
            "https://docs.standx.com/standx-api/standx-api",
        ],
        "reason": "SIP-2 Position Yield is marked Implemented and rewards eligible open perpetual positions over time. StandX exposes official APIs for opening and managing perpetual positions programmatically.",
        "next_action": "Prepare a capped eligible-position plan with holding-time, leverage, funding and liquidation limits; do not open a position until explicit financial/legal approval.",
        "known_cost_risk": "Requires genuine open perpetual exposure. Costs/risks include trading fees, spread/slippage, funding, mark-to-market loss and liquidation risk; reward pool parameters are configurable.",
        "missing_approval": "Explicit approval for real perps exposure, capital/margin use, wallet/API signing, leverage cap, and Japan/Terms eligibility.",
        "requires_wallet_signature": True,
    },
    "decibel-trading": {
        "state": "APPROVAL_REQUIRED_FINANCIAL",
        "verified_at": "2026-08-12",
        "sources": [
            "https://docs.decibel.trade/rewards/amps",
            "https://docs.decibel.trade/rewards/overview",
            "https://docs.decibel.trade/quickstart/api-reference",
            "https://docs.decibel.trade/api-reference/rest/overview",
        ],
        "reason": "Decibel Amps Season 1 is the current points program; organic trading accrues Amps daily. Decibel's official REST/WebSocket API explicitly supports programmatic order management and exposes trading-points/Amps endpoints.",
        "next_action": "Prepare a capped organic-trading plan and estimate all-in cost per expected Amp; do not send orders until explicit financial/legal approval.",
        "known_cost_risk": "Requires real trading activity and market exposure. Costs/risks include trading fees, spread/slippage, funding, leverage/liquidation and uncertain future token value; rapid in-and-out cycling is deprioritized by the scoring model.",
        "missing_approval": "Explicit approval for real trading exposure, capital use, API credentials/signing as required by the account, and Japan/Terms eligibility.",
        "requires_wallet_signature": False,
    },
    "decibel-liquidity": {
        "state": "APPROVAL_REQUIRED_ASSET_MOVE",
        "verified_at": "2026-08-12",
        "sources": [
            "https://docs.decibel.trade/rewards/amps",
            "https://docs.decibel.trade/rewards/overview",
        ],
        "reason": "Decibel Amps Season 1 explicitly allocates points to liquidity provision, including capital committed to the DLP Vault or user-managed vaults.",
        "next_action": "Prepare a capped DLP/vault allocation plan with lock-up, withdrawal and smart-contract risk limits; do not deposit or approve assets until explicit approval.",
        "known_cost_risk": "Requires capital commitment and onchain/vault exposure. Risks include smart-contract/vault risk, liquidity/withdrawal mechanics, strategy losses and capital lock-up; future token value remains uncertain.",
        "missing_approval": "Explicit approval for deposit/asset movement, any token approval or wallet signature, capital cap, and Japan/Terms eligibility.",
        "requires_wallet_signature": True,
    },
    "grvt": {
        "state": "APPROVAL_REQUIRED_FINANCIAL",
        "verified_at": "2026-08-12",
        "sources": [
            "https://help.grvt.io/en/articles/12332040-live-rewards-season-2-0",
            "https://help.grvt.io/en/articles/15583631-how-rewards-are-calculated-on-grvt",
            "https://api-docs.grvt.io/trading_api/",
            "https://help.grvt.io/en/articles/9614688-what-are-api-keys",
        ],
        "reason": "GRVT Rewards Season 2.0 is explicitly live. Perpetual trading earns points, API-based trades are explicitly eligible but earn fewer points than UI trades, and the official Trading API supports signed programmatic order submission.",
        "next_action": "Prepare a capped perps API-trading plan that compares the lower API point rate against fees, funding and risk; do not create a live order or sign a payload until explicit approval.",
        "known_cost_risk": "API trades earn fewer points than UI trades. Level-1 perps fees published in June 2026 are approximately -0.0001% maker rebate and 0.0450% taker, before spread/slippage/funding; positions also carry market and liquidation risk.",
        "missing_approval": "Explicit approval for real perps exposure, account/API private-key signing, capital/leverage limits, and Japan/Terms eligibility.",
        "requires_wallet_signature": True,
    },
}


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
        "verification_sources": [],
        "earning_path_verified_at": None,
        "known_cost_risk": None,
        "missing_approval": None,
    }

    # Hard-block explicit conflicts and explicit unverified reward mechanics.
    # A dedicated current verification must never override a conflict/UNVERIFIED state.
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

    current_verification = CURRENT_EARNING_VERIFICATION.get(slug)
    if current_verification:
        return {
            **base,
            "acquisition_state": current_verification["state"],
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_wallet_signature": bool(current_verification["requires_wallet_signature"]),
            "verification_sources": list(current_verification["sources"]),
            "earning_path_verified_at": current_verification["verified_at"],
            "known_cost_risk": current_verification["known_cost_risk"],
            "missing_approval": current_verification["missing_approval"],
            "next_action": current_verification["next_action"],
            "reason": current_verification["reason"],
        }

    # Wave 1 Pacifica/Hibachi have separately verified mechanics in airdrop_agents,
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
            "known_cost_risk": "Requires genuine exchange activity with fees, spread/slippage, funding or price risk depending on the market; future reward value is unknown.",
            "missing_approval": "Explicit approval for real trading exposure, capital/risk caps, any required signing/authentication, and Japan/Terms eligibility.",
            "reason": "Current official reward mechanics require genuine exchange activity; this creates economic exposure and can require signed/authenticated orders.",
        }

    if mode == "SCOUT":
        return {
            **base,
            "acquisition_state": "DISCOVERY_ONLY",
            "next_action": "Continue discovery and promote a candidate only after an exact qualifying action is verified.",
            "reason": "This adapter is a discovery source, not an earning executor.",
        }

    # Remaining Wave 2/3 adapters have not yet had current mechanics/lifecycle
    # promoted from REVERIFY. Keep them distinct from hard-blocked/conflicted targets.
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
            "known_cost_risk": "Requires capital movement or lock-up; exact contract, liquidity and market risks must be verified before execution.",
            "missing_approval": "Explicit approval for asset movement/signing and Japan/Terms eligibility.",
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
        "current_verified_earning_path_count": len(CURRENT_EARNING_VERIFICATION),
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
