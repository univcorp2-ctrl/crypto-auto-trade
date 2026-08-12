from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
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
# No current target meets that standard. Keep this registry empty until an
# adapter is verified against current primary documentation and covered by tests.
SAFE_AUTO_ACTIONS: dict[str, dict[str, Any]] = {}

# Primary-source reward mechanics verified during the scheduled acquisition
# review. These entries DO NOT authorize execution. They only move a target from
# a generic REVERIFY state into the appropriate approval queue with the exact
# financial/asset-movement risk made explicit.
#
# Evidence is deliberately short-lived. After the TTL, the target falls back to
# REVERIFY_REQUIRED until current official documentation is checked again.
VERIFICATION_TTL_DAYS = 7
VERIFIED_GATED_ACTIONS: dict[str, dict[str, Any]] = {
    "hyprearn": {
        "verified_at": "2026-08-12T04:24:23+00:00",
        "evidence_source": "https://hyprearn.com/",
        "evidence_note": "Official HyprEarn pages state that curated agents run strategies across multiple perpetual DEXs, users allocate capital into those agents to pursue yield and stack DEX points, and every executed trade contributes to HyprEarn points.",
        "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
        "requires_funds": True,
        "requires_real_order": True,
        "requires_asset_move": True,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_TERMS_JURISDICTION_AND_AGENT_RISK",
        "known_cost_or_risk": "Qualification requires capital allocation and the delegated agents subsequently trade perpetuals. This creates strategy/PnL, fee, funding, liquidation, smart-contract/custody-interface and withdrawal/liquidity risk; point and yield outcomes are not guaranteed.",
        "missing_approval": "Current terms/jurisdiction and wallet/authentication check plus explicit allocation amount, maximum acceptable loss, withdrawal tolerance and delegated-agent risk approval.",
        "next_action": "Verify current account eligibility, wallet/authentication and agent/vault withdrawal mechanics, then prepare a capped allocation plan for explicit approval; do not connect/sign a wallet, allocate capital or launch trading agents automatically.",
    },
    "standx-maker": {
        "verified_at": "2026-08-12T03:25:00+00:00",
        "evidence_source": "https://docs.standx.com/docs/standx-perps-solutions/community-maker-yield",
        "evidence_note": "Official live parameters require real executable two-sided orders within 10 bps and at least 30 qualifying minutes per hour; yield is settled daily.",
        "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
        "requires_funds": True,
        "requires_real_order": True,
        "requires_asset_move": False,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_PERPS_USER_ELIGIBILITY",
        "known_cost_or_risk": "Real maker orders can fill and create directional exposure, adverse selection, funding, margin and liquidation risk. Per-pair minimum qualifying sizes and caps vary; no live quoting is authorized.",
        "missing_approval": "Explicit approval of account eligibility, authentication/signing method, maximum notional and maximum loss before any real maker order.",
        "next_action": "Re-check current Perps user eligibility and authentication, then prepare a capped genuine two-sided maker plan for explicit approval; do not place orders automatically.",
    },
    "standx-position": {
        "verified_at": "2026-08-12T04:24:23+00:00",
        "evidence_source": "https://docs.standx.com/sip/sip-2-position-yield",
        "evidence_note": "Official SIP-2 is marked Implemented and allocates Position Yield only to valid open perpetual positions that satisfy holding, risk-state, supported-market and rewardable-leverage rules; a position must experience at least one complete funding settlement cycle before accrual.",
        "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
        "requires_funds": True,
        "requires_real_order": True,
        "requires_asset_move": False,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_PERPS_USER_ELIGIBILITY_AND_LIVE_PARAMETERS",
        "known_cost_or_risk": "Earning requires opening and holding a real perpetual position. That creates directional PnL, funding, margin, liquidation and parameter-change risk; the fee-pool ratio, supported markets, minimum hold time, leverage limits and settlement mechanism are configurable.",
        "missing_approval": "Current account eligibility/authentication and live SIP-2 parameter check plus explicit market, side, maximum notional, leverage, holding duration and maximum loss.",
        "next_action": "Re-check current eligible markets and live SIP-2 parameters, then prepare a capped genuine position-holding plan for explicit approval; do not open or hold a real position automatically.",
    },
    "decibel-trading": {
        "verified_at": "2026-08-12T03:25:00+00:00",
        "evidence_source": "https://docs.decibel.trade/rewards/amps",
        "evidence_note": "Official Amps Season 1 documentation says Amps accrue daily from organic trading activity and explicitly weights leverage, holding duration, market exploration and consistency.",
        "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
        "requires_funds": True,
        "requires_real_order": True,
        "requires_asset_move": False,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_TERMS_AND_JURISDICTION",
        "known_cost_or_risk": "Perpetual trading creates PnL, fee, funding, leverage and liquidation risk. Exact Amps formulas are intentionally undisclosed, so reward-per-dollar cannot be guaranteed.",
        "missing_approval": "Current terms/jurisdiction and authentication check plus explicit maximum notional, fee budget and maximum loss.",
        "next_action": "Verify current user eligibility and authentication, then prepare a capped organic-trading plan for explicit approval; do not submit real orders automatically.",
    },
    "decibel-liquidity": {
        "verified_at": "2026-08-12T03:25:00+00:00",
        "evidence_source": "https://docs.decibel.trade/rewards/amps",
        "evidence_note": "Official Amps Season 1 documentation says providing capital to the DLP Vault or user-managed vaults accrues a dedicated portion of daily emissions based on depth and duration.",
        "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
        "requires_funds": True,
        "requires_real_order": False,
        "requires_asset_move": True,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_TERMS_AND_JURISDICTION",
        "known_cost_or_risk": "Qualifying requires committing capital to a vault. Capital can face vault/strategy loss, withdrawal constraints and opportunity cost; reward formulas are not guaranteed.",
        "missing_approval": "Current terms/jurisdiction and authentication check plus explicit deposit amount, maximum acceptable loss and lock/withdrawal tolerance.",
        "next_action": "Verify current user eligibility, vault mechanics and authentication, then prepare a capped deposit plan for explicit approval; do not move assets automatically.",
    },
    "grvt": {
        "verified_at": "2026-08-12T03:25:00+00:00",
        "evidence_source": "https://help.grvt.io/en/articles/12332040-live-rewards-season-2-0",
        "evidence_note": "Official live Rewards Season 2.0 states trading earns points and explicitly says API-based trades earn points, although less than UI-based trades.",
        "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
        "requires_funds": True,
        "requires_real_order": True,
        "requires_asset_move": False,
        "authentication_recheck_required": True,
        "terms_status": "JAPAN_NOT_LISTED_IN_CURRENT_RESTRICTED_JURISDICTIONS_ACCOUNT_ELIGIBILITY_STILL_REVERIFY",
        "known_cost_or_risk": "Real perpetual trading creates PnL, funding, slippage and liquidation risk. Current Level 1 perps fees are maker -0.0001% and taker 0.0450%; actual all-in cost can be higher.",
        "missing_approval": "Account-specific eligibility/authentication check plus explicit maximum notional, fee budget and maximum loss.",
        "next_action": "Confirm account eligibility and authentication, then prepare a capped genuine API-trading plan for explicit approval; do not submit real orders automatically.",
    },
    "lighter": {
        "verified_at": "2026-08-12T09:25:35+00:00",
        "evidence_source": "https://docs.lighter.xyz/points-program",
        "evidence_note": "Current official general Points Program says Season 2 points are distributed every Friday and organic trading strategies via UI and API earn points. The current Retail page also describes weekly Season 2 distributions; the separate Market Makers page's 2025-12-26 end statement applies to that market-maker track rather than the current retail/API organic-trading path.",
        "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
        "requires_funds": True,
        "requires_real_order": True,
        "requires_asset_move": False,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_TERMS_JURISDICTION_ACCOUNT_AND_LIVE_POINTS_PARAMETERS",
        "known_cost_or_risk": "Earning requires genuine trading. Real perpetual trading creates fee, spread/slippage, funding, margin, liquidation and directional PnL risk; the points formula/weights can change and no fixed reward-per-dollar is guaranteed.",
        "missing_approval": "Current terms/jurisdiction, account eligibility and API authentication check plus explicit market, maximum notional, fee budget, leverage and maximum loss.",
        "next_action": "Confirm current account eligibility, API authentication and live Retail points parameters, then prepare a capped organic API-trading plan for explicit approval; do not submit real orders automatically and never use Sybil, self-trading or manipulative activity.",
    },
    "nado-trading": {
        "verified_at": "2026-08-12T05:25:00+00:00",
        "evidence_source": "https://docs.nado.xyz/points/season-1",
        "evidence_note": "Official Nado Season 1 documentation describes a recurring weekly points program and says genuine trading, market making, liquidations and other system-supporting trading activity earn points; wash trading and self-matching are explicitly ineligible.",
        "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
        "requires_funds": True,
        "requires_real_order": True,
        "requires_asset_move": False,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_TERMS_JURISDICTION_ACCOUNT_AND_API_ELIGIBILITY",
        "known_cost_or_risk": "Qualification requires genuine market activity. Real spot/perpetual trading creates fee, spread/slippage, funding, margin, liquidation and directional PnL risk; point allocation is activity-based rather than a guaranteed reward-per-dollar formula.",
        "missing_approval": "Current terms/jurisdiction, account/authentication and API-reward eligibility check plus explicit market, maximum notional, fee budget, leverage and maximum loss.",
        "next_action": "Verify current user/account and API eligibility, then prepare a capped genuine-trading plan for explicit approval; do not submit real orders automatically and do not use self-matching or wash activity.",
    },
    "nado-nlp": {
        "verified_at": "2026-08-12T05:25:00+00:00",
        "evidence_source": "https://docs.nado.xyz/points/season-1",
        "evidence_note": "Official Nado Season 1 documentation says NLP participants earn points based on their average proportional share of the vault during each weekly epoch; current NLP documentation describes USDT0 deposits being deployed into active liquidity strategies and a post-mint withdrawal lock.",
        "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
        "requires_funds": True,
        "requires_real_order": False,
        "requires_asset_move": True,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_TERMS_JURISDICTION_ACCOUNT_AND_CURRENT_VAULT_PARAMETERS",
        "known_cost_or_risk": "Qualification requires depositing capital into NLP. Capital is exposed to vault/strategy PnL, withdrawal gating or lock periods, smart-contract/oracle risk and opportunity cost; current vault caps and parameters can change.",
        "missing_approval": "Current terms/jurisdiction, account/authentication, vault cap/lock/withdrawal mechanics plus explicit deposit amount, maximum acceptable loss and liquidity tolerance.",
        "next_action": "Verify current user eligibility and live NLP vault parameters, then prepare a capped deposit plan for explicit approval; do not deposit, sign or move assets automatically.",
    },
    "ethereal-margin": {
        "verified_at": "2026-08-12T05:25:00+00:00",
        "evidence_source": "https://docs.ethereal.trade/points/ethereal-points",
        "evidence_note": "Official Ethereal Rewards & Points documentation says users automatically earn rewards by holding USDe margin, and the current Season One documentation lists holding USDe margin as a core points-earning activity during mainnet/public-beta epochs.",
        "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
        "requires_funds": True,
        "requires_real_order": False,
        "requires_asset_move": True,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_TERMS_JURISDICTION_ACCOUNT_AND_CURRENT_SEASON_PARAMETERS",
        "known_cost_or_risk": "Qualification requires maintaining USDe margin on Ethereal. Moving/holding capital creates stablecoin, smart-contract/platform, withdrawal/liquidity and opportunity-cost risk; points and reward rates can change by epoch or program parameters.",
        "missing_approval": "Current terms/jurisdiction, account/authentication and live Season One/points parameters plus explicit deposit amount, maximum acceptable loss and withdrawal tolerance.",
        "next_action": "Verify current user eligibility and live points/reward parameters, then prepare a capped USDe-margin allocation for explicit approval; do not deposit, sign or move assets automatically.",
    },
    "reya-staking": {
        "verified_at": "2026-08-12T06:24:02+00:00",
        "evidence_source": "https://docs.reya.xyz/reya-token/reya-chain-points-faqs",
        "evidence_note": "Official Reya Chain Points FAQs state that staking earns RCP by converting rUSD into srUSD and holding it in the margin account or supported third-party applications; weekly distributions use a snapshot, and unstaking before the snapshot forfeits staking RCP for that week.",
        "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
        "requires_funds": True,
        "requires_real_order": False,
        "requires_asset_move": True,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_CURRENT_PROGRAM_LIFECYCLE_TERMS_JURISDICTION_ACCOUNT_AND_STAKING_PARAMETERS",
        "known_cost_or_risk": "Qualification requires converting and holding capital as srUSD. This creates protocol/stablecoin, smart-contract, liquidity/withdrawal, snapshot-timing and opportunity-cost risk; reward weights and program parameters can change.",
        "missing_approval": "Current program lifecycle, terms/jurisdiction, account/wallet authentication, conversion/redemption mechanics and live RCP parameters plus explicit allocation amount, maximum acceptable loss and liquidity tolerance.",
        "next_action": "Re-check current RCP lifecycle, account eligibility and srUSD conversion/redemption mechanics, then prepare a capped staking allocation for explicit approval; do not convert, sign, deposit or move assets automatically.",
    },
    "extended-trading": {
        "verified_at": "2026-08-12T06:24:02+00:00",
        "evidence_source": "https://docs.extended.exchange/extended-resources/points",
        "evidence_note": "Official Extended Points documentation lists organic trading activity as a points-earning category and describes weekly points distributions; current migration documentation also states that existing points balances remain accessible on the Starknet instance.",
        "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
        "requires_funds": True,
        "requires_real_order": True,
        "requires_asset_move": False,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_CURRENT_PROGRAM_LIFECYCLE_TERMS_JURISDICTION_ACCOUNT_AND_AUTHENTICATION",
        "known_cost_or_risk": "Qualification requires genuine trading activity. Real perpetual trading creates fees, spread/slippage, funding, margin, liquidation and directional PnL risk; weekly point-allocation criteria can change and no fixed reward-per-dollar is guaranteed.",
        "missing_approval": "Current points-program lifecycle, terms/jurisdiction, account/authentication and live fee/points parameters plus explicit market, maximum notional, fee budget, leverage and maximum loss.",
        "next_action": "Confirm the points program is currently accruing for the account and re-check eligibility/authentication, then prepare a capped genuine-trading plan for explicit approval; do not submit real orders automatically.",
    },
    "extended-liquidity": {
        "verified_at": "2026-08-12T06:24:02+00:00",
        "evidence_source": "https://docs.extended.exchange/extended-resources/points",
        "evidence_note": "Official Extended Points documentation lists providing liquidity as a points-earning category, including depositing funds into a vault or providing tight liquidity in relevant markets; official vault documentation describes capital being used for market making and liquidations.",
        "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
        "requires_funds": True,
        "requires_real_order": False,
        "requires_asset_move": True,
        "authentication_recheck_required": True,
        "terms_status": "REVERIFY_CURRENT_PROGRAM_LIFECYCLE_TERMS_JURISDICTION_ACCOUNT_AND_VAULT_PARAMETERS",
        "known_cost_or_risk": "The vault path requires committing capital. Capital can face strategy/market-making/liquidation loss, smart-contract/platform risk, withdrawal or liquidity constraints and opportunity cost; weekly points allocation can change.",
        "missing_approval": "Current points-program lifecycle, terms/jurisdiction, account/authentication, vault availability/cap/withdrawal mechanics plus explicit deposit amount, maximum acceptable loss and liquidity tolerance.",
        "next_action": "Confirm the points program is currently accruing and verify live vault/account parameters, then prepare a capped vault-deposit plan for explicit approval; do not sign, deposit or move assets automatically.",
    },
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _verified_spec_is_fresh(spec: dict[str, Any], *, now: datetime) -> bool:
    verified_at = datetime.fromisoformat(str(spec["verified_at"]))
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    verified_at = verified_at.astimezone(UTC)
    current_time = now.astimezone(UTC)
    return verified_at <= current_time <= verified_at + timedelta(days=VERIFICATION_TTL_DAYS)


def _classify_target(target: dict[str, Any], *, now: datetime) -> dict[str, Any]:
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
        "requires_real_order": False,
        "requires_asset_move": False,
        "authentication_recheck_required": False,
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

    verified_spec = VERIFIED_GATED_ACTIONS.get(slug)
    if verified_spec and _verified_spec_is_fresh(verified_spec, now=now):
        expires_at = datetime.fromisoformat(str(verified_spec["verified_at"])).astimezone(UTC) + timedelta(days=VERIFICATION_TTL_DAYS)
        return {
            **base,
            **verified_spec,
            "evidence_status": "PRIMARY_VERIFIED_CURRENT",
            "verification_expires_at": expires_at.isoformat(),
            "requires_user_approval": True,
            "reason": verified_spec["evidence_note"],
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
            "requires_real_order": True,
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
            "requires_asset_move": True,
            "next_action": "Verify current reward rules, then prepare any deposit/stake/liquidity action for explicit approval.",
            "reason": "The configured target is read-only because earning may require asset movement or capital lock-up.",
        }

    return {
        **base,
        "acquisition_state": "REVERIFY_REQUIRED",
        "next_action": "Verify current earning action, Japan/Terms eligibility, costs and required authentication before implementing acquisition.",
        "reason": "No currently verified zero-value-transfer, no-signature acquisition adapter is implemented for this target.",
    }


def build_acquisition_report(status_report: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    current_time = now or datetime.now(UTC)
    actions = [_classify_target(target, now=current_time) for target in status_report.get("targets", [])]
    return {
        "generated_at": current_time.astimezone(UTC).isoformat(),
        "mode": "ACQUISITION_GATED",
        "objective": "Execute only verified non-financial/no-signature reward actions automatically; queue financial or signing actions for approval.",
        "target_count": len(actions),
        "safe_auto_adapter_count": len(SAFE_AUTO_ACTIONS),
        "verified_gated_action_count": sum(item.get("evidence_status") == "PRIMARY_VERIFIED_CURRENT" for item in actions),
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
                "verified_gated_action_count": report["verified_gated_action_count"],
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
