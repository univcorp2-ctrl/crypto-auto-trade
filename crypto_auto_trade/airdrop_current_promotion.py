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

# These primary-source checks were refreshed immediately before or after their
# older base-registry TTLs expired. They remain approval-only: every reward path
# below requires real economic activity or asset movement, and none enables a
# safe automatic acquisition action.
HYPREARN_VERIFIED_AT = "2026-08-19T04:24:00+00:00"
HYPREARN_EVIDENCE_SOURCE = "https://hyprearn.com/"
STANDX_POSITION_VERIFIED_AT = "2026-08-19T04:24:00+00:00"
STANDX_POSITION_EVIDENCE_SOURCE = "https://docs.standx.com/sip/sip-2-position-yield"
REYA_STAKING_VERIFIED_AT = "2026-08-19T07:56:34+00:00"
REYA_STAKING_EVIDENCE_SOURCE = "https://blog.reya.network/ethena-and-reya-a-new-foundation-for-rlp/"
REYA_STAKING_RCP_SOURCE = "https://docs.reya.xyz/reya-token/reya-chain-points-faqs"
REYA_STAKING_PARTNERSHIP_SOURCE = "https://blog.reya.network/reyas-strategic-partnerships/"
LIGHTER_VERIFIED_AT = "2026-08-19T12:18:26+00:00"
LIGHTER_EVIDENCE_SOURCE = "https://docs.lighter.xyz/points-program"
LIGHTER_RETAIL_SOURCE = "https://docs.lighter.xyz/points-program/retail"
LIGHTER_API_SOURCE = "https://docs.lighter.xyz/perpetual-futures/api"


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


def _promote_reverify_action(
    report: dict[str, Any],
    *,
    slug: str,
    verified_at: str,
    evidence_source: str,
    fields: dict[str, Any],
    now: datetime,
) -> bool:
    if not _verified_at_is_fresh(verified_at, now=now):
        return False

    expires = (
        datetime.fromisoformat(verified_at).astimezone(UTC)
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
                "verified_at": verified_at,
                "evidence_checked_at": verified_at,
                "evidence_source": evidence_source,
                "evidence_status": "PRIMARY_VERIFIED_CURRENT",
                "verification_expires_at": expires.isoformat(),
                "action_taken": "NONE",
                "auto_executed": False,
            }
        )
        return True
    return False


def promote_current_verified_paths(
    report: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Promote only still-current primary-source overlays; never execute an action.

    The base acquisition registry and the current evidence overlays intentionally
    use independent TTLs. Fresher primary evidence must be able to keep a target
    in the appropriate approval queue when an older base entry expires. Promotion
    never relaxes the financial/signing boundary and never performs an acquisition.
    """

    current = now or datetime.now(UTC)
    result = copy.deepcopy(report)
    result["current_evidence_promotion_count"] = 0

    if _promote_reverify_action(
        result,
        slug="standx-maker",
        verified_at=STANDX_MAKER_VERIFIED_AT,
        evidence_source=STANDX_MAKER_EVIDENCE_SOURCE,
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_real_order": True,
            "requires_asset_move": False,
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
        },
    ):
        result["current_evidence_promotion_count"] += 1

    if _promote_reverify_action(
        result,
        slug="hyprearn",
        verified_at=HYPREARN_VERIFIED_AT,
        evidence_source=HYPREARN_EVIDENCE_SOURCE,
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_wallet_signature": True,
            "requires_real_order": True,
            "requires_asset_move": True,
            "authentication_recheck_required": True,
            "evidence_note": (
                "Current official HyprEarn site states that users allocate capital into curated agents that "
                "run strategies across multiple perpetual DEXs to pursue yield and stack DEX points, and that "
                "every executed trade contributes to HyprEarn points. This is an earning path, but it requires "
                "capital allocation and delegated real perpetual trading rather than a zero-value-transfer action."
            ),
            "terms_status": (
                "REVERIFY_CURRENT_TERMS_JURISDICTION_ACCOUNT_WALLET_AUTHENTICATION_"
                "AGENT_RISK_AND_WITHDRAWAL_MECHANICS_BEFORE_EXECUTION"
            ),
            "known_cost_or_risk": (
                "Qualification requires allocating capital to a trading agent that can execute real perpetual "
                "strategies across third-party DEXs. Risks include strategy/directional PnL, fees, funding, "
                "liquidation, smart-contract/interface risk, withdrawal or liquidity constraints, wallet/signing "
                "risk and opportunity cost. DEX points, HyprEarn points and yield are not guaranteed to have a "
                "fixed or positive value."
            ),
            "missing_approval": (
                "Current HyprEarn Terms/jurisdiction and account eligibility, supported wallet/authentication and "
                "exact transaction/signing flow, selected agent and underlying DEX exposure, withdrawal mechanics, "
                "plus explicit allocation amount, leverage limits, fee/funding budget, maximum acceptable loss and "
                "liquidity/withdrawal tolerance."
            ),
            "next_action": (
                "Before any economic action, review the current HyprEarn Terms and authenticated agent details, "
                "identify the exact allocation/signing and withdrawal flow and underlying DEX strategy exposure, "
                "then prepare a capped allocation plan for explicit approval. Do not connect/sign a wallet, allocate "
                "capital, deposit assets or launch an agent automatically."
            ),
        },
    ):
        result["current_evidence_promotion_count"] += 1

    if _promote_reverify_action(
        result,
        slug="standx-position",
        verified_at=STANDX_POSITION_VERIFIED_AT,
        evidence_source=STANDX_POSITION_EVIDENCE_SOURCE,
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_real_order": True,
            "requires_asset_move": False,
            "authentication_recheck_required": True,
            "evidence_note": (
                "Current official StandX SIP-2 remains marked Implemented and allocates Position Yield to eligible "
                "open perpetual positions regardless of opening path when protocol qualification and risk controls "
                "are satisfied. A position must experience at least one complete funding settlement cycle before "
                "it can accrue Position Yield."
            ),
            "terms_status": (
                "REVERIFY_CURRENT_STANDX_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_AUTHENTICATION_"
                "AND_LIVE_SIP2_PARAMETERS_BEFORE_EXECUTION"
            ),
            "known_cost_or_risk": (
                "Earning requires opening and maintaining a real perpetual position through at least the applicable "
                "qualification period. This creates directional PnL, fees, spread/slippage, funding, margin and "
                "liquidation risk; supported markets, rewardable leverage, fee-pool allocation, hold/cooldown rules "
                "and settlement parameters are configurable and can change."
            ),
            "missing_approval": (
                "Current StandX Terms/jurisdiction and account eligibility, authentication/signing method and live "
                "SIP-2 parameters, plus explicit market, side, maximum notional, leverage, minimum/maximum holding "
                "duration, fee/funding budget and maximum acceptable loss."
            ),
            "next_action": (
                "Immediately before any economic action, re-open the current SIP-2 and live StandX market/account "
                "parameters, confirm the eligible market and qualification window, calculate capped worst-case "
                "fee/funding/liquidation exposure, and prepare the position plan for explicit approval only. Do not "
                "open, hold, modify or close a real position automatically for reward acquisition."
            ),
        },
    ):
        result["current_evidence_promotion_count"] += 1

    if _promote_reverify_action(
        result,
        slug="lighter",
        verified_at=LIGHTER_VERIFIED_AT,
        evidence_source=LIGHTER_EVIDENCE_SOURCE,
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_wallet_signature": True,
            "requires_real_order": True,
            "requires_asset_move": False,
            "authentication_recheck_required": True,
            "evidence_sources": [
                LIGHTER_EVIDENCE_SOURCE,
                LIGHTER_RETAIL_SOURCE,
                LIGHTER_API_SOURCE,
            ],
            "source_coverage": "CURRENT_PRIMARY_OFFICIAL_ONLY_NO_INDEPENDENT_EXPERT_SOURCE",
            "reward_scope": "CURRENT_RETAIL_SEASON2_ORGANIC_UI_API_TRADING",
            "retail_weekly_points": 200000,
            "retail_activity_window": "WEDNESDAY_TO_TUESDAY",
            "retail_activity_factors": [
                "volume",
                "open_interest",
                "fundings",
                "liquidations_and_deleverages",
                "pnl",
            ],
            "retail_formula_characteristics": (
                "NONLINEAR_MARKET_AND_TIME_BUCKET_SPECIFIC_WITH_QUALITY_AND_PREMIUM_SCALING"
            ),
            "evidence_note": (
                "Current official Lighter Points Program says Season 2 points are distributed every Friday "
                "and organic trading strategies via both UI and API earn points. The current Retail page says "
                "200,000 points are distributed to retail traders each week for Wednesday-through-Tuesday "
                "activity and considers Volume, Open Interest, Fundings, Liquidations/Deleverages and PnL. "
                "It also says points are nonlinear, can vary by market and time bucket, and intentionally "
                "losing money or getting liquidated is not beneficial. The separate Market Makers page's "
                "December 26, 2025 end date is scoped to the market-maker track, not the current Retail path."
            ),
            "terms_status": (
                "REVERIFY_CURRENT_LIGHTER_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_"
                "API_KEY_WALLET_AUTHENTICATION_AND_LIVE_RETAIL_WEIGHTS_BEFORE_EXECUTION"
            ),
            "known_cost_or_risk": (
                "Qualification requires genuine trading and therefore real economic exposure. Even where a "
                "current account tier displays zero trading fees, spread/slippage, funding, margin, liquidation "
                "and directional PnL risk remain, and point value plus scoring weights are not fixed. Creating "
                "or linking a Lighter account can require an Ethereum-wallet signature, and API requests use "
                "account-owned signing keys. No wallet signature, API-key setup or real order is authorized here."
            ),
            "missing_approval": (
                "Current Lighter Terms/jurisdiction and account eligibility; whether an already-authenticated "
                "account and compliant API key already exist or a wallet-linking signature would be required; "
                "the live Retail scoring/account-tier parameters; and explicit market, maximum notional, leverage, "
                "fee/spread/funding budget and maximum acceptable loss before any genuine order."
            ),
            "next_action": (
                "Immediately before any economic action, re-open the current Lighter Points and Retail pages plus "
                "Terms/account eligibility, confirm the authenticated account/API-key state and live scoring inputs, "
                "then prepare a capped genuine-trading plan for explicit approval. Do not create/link a wallet "
                "session, sign a message, deposit funds or submit real orders automatically, and never use Sybil, "
                "self-trading or manipulative activity."
            ),
        },
    ):
        result["current_evidence_promotion_count"] += 1

    if _promote_reverify_action(
        result,
        slug="reya-staking",
        verified_at=REYA_STAKING_VERIFIED_AT,
        evidence_source=REYA_STAKING_EVIDENCE_SOURCE,
        now=current,
        fields={
            "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE",
            "requires_user_approval": True,
            "requires_funds": True,
            "requires_wallet_signature": True,
            "requires_real_order": False,
            "requires_asset_move": True,
            "authentication_recheck_required": True,
            "evidence_sources": [
                REYA_STAKING_EVIDENCE_SOURCE,
                REYA_STAKING_RCP_SOURCE,
                REYA_STAKING_PARTNERSHIP_SOURCE,
            ],
            "source_coverage": "CURRENT_PRIMARY_OFFICIAL_ONLY_NO_INDEPENDENT_EXPERT_SOURCE",
            "evidence_note": (
                "Current official Reya RLP documentation says users can become LPs by depositing USDC into the "
                "Reya Liquidity Pool, which converts pool assets into USDe/sUSDe for liquidity and market-making "
                "use; the pool accrues Ethena yield, Reya market-making returns, trade/liquidation fees and Reya "
                "Chain Points, with returns shared among LPs based on deposited amount. The current RCP FAQ still "
                "describes the same staking reward track using legacy rUSD/srUSD names, while newer official Reya "
                "materials state rUSD was renamed to USDC and srUSD to RLP. This refresh therefore treats the "
                "current RLP liquidity-pool deposit as the asset-movement reward path rather than the stale "
                "rUSD-to-srUSD wording."
            ),
            "terms_status": (
                "REVERIFY_CURRENT_REYA_TERMS_JURISDICTION_ACCOUNT_ELIGIBILITY_AUTHENTICATION_"
                "RLP_DEPOSIT_REDEMPTION_FEES_AND_SIGNING_BEFORE_EXECUTION"
            ),
            "known_cost_or_risk": (
                "Earning through the current RLP path requires moving capital into the Reya Liquidity Pool. Pool "
                "assets are deployed through USDe/sUSDe and Reya market-making/liquidity strategies, so risks can "
                "include stablecoin/depeg and counterparty exposure, strategy/market-making PnL, smart-contract/"
                "platform risk, withdrawal/liquidity constraints, fees, wallet/signing risk and opportunity cost. "
                "RCP and other pool returns have no guaranteed fixed value and must not be assumed to offset losses."
            ),
            "missing_approval": (
                "Current Reya Terms/jurisdiction and account eligibility; the authenticated wallet/account flow and "
                "exact transaction/signing requirements; current RLP deposit, mint, redemption/withdrawal and fee "
                "mechanics; confirmation that the account-specific RLP position remains eligible for current RCP; "
                "plus explicit USDC allocation amount, maximum acceptable loss and liquidity/withdrawal tolerance."
            ),
            "next_action": (
                "Immediately before any economic action, re-open the current official RLP/RCP materials and the "
                "authenticated Reya LP interface, confirm current Terms/account eligibility plus the exact USDC "
                "deposit, RLP mint, redemption/withdrawal, fee and signing flow, and verify current RCP treatment. "
                "Then prepare a capped USDC allocation for explicit approval only. Do not deposit, bridge, approve "
                "tokens, sign a wallet message or transaction, redeem, withdraw or move assets automatically."
            ),
        },
    ):
        result["current_evidence_promotion_count"] += 1

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
