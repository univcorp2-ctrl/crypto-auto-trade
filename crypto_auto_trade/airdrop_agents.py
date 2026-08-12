from __future__ import annotations

import argparse
import json
import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "airdrop" / "latest.json"


@dataclass(frozen=True)
class AirdropTarget:
    slug: str
    name: str
    mode: str
    priority: str
    program_url: str
    api_url: str | None
    reward_unit: str
    wave: int
    seed_note: str


TARGETS: tuple[AirdropTarget, ...] = (
    AirdropTarget("okx-ai", "OKX.AI Airdrop Hunter Scout", "SCOUT", "A", "https://www.okx.ai/zh-hans/agents/2175", None, "candidate", 3, "Discovery-only seed; never executes wallet actions."),
    AirdropTarget("hyprearn", "HyprEarn Multi-DEX Points Vault", "READ_ONLY", "B", "https://hyprearn.com/", None, "points/yield", 3, "Third-party vault research only; deposits remain human-gated."),
    AirdropTarget("pacifica", "Pacifica API Points Trader", "DRY_RUN", "S", "https://pacifica.gitbook.io/docs/programs/points-program", "https://docs.pacifica.fi/api-documentation", "points", 1, "Wave 1. Re-verify current API reward eligibility before any live use."),
    AirdropTarget("hibachi", "Hibachi API Points Trader", "DRY_RUN", "S", "https://docs.hibachi.xyz/hibachi-rewards/hibachi-points", "https://docs.hibachi.xyz/hibachi-docs/api-and-developer-tools", "points", 1, "Wave 1. Re-verify current API/UI points treatment before any live use."),
    AirdropTarget("standx-maker", "StandX Community Maker Yield Bot", "DRY_RUN", "A", "https://docs.standx.com/docs/standx-perps-solutions/community-maker-yield", "https://docs.standx.com/", "reward", 2, "Two-sided maker simulation only; no self-match or quote stuffing."),
    AirdropTarget("standx-position", "StandX Position Yield Agent", "READ_ONLY", "B", "https://docs.standx.com/sip/sip-2-position-yield", "https://docs.standx.com/", "yield", 2, "Position carry monitor; opening exposure remains human-gated."),
    AirdropTarget("decibel-trading", "Decibel Trading Amps Agent", "DRY_RUN", "S", "https://docs.decibel.trade/rewards/amps", "https://docs.decibel.trade/", "amps", 2, "Measure all-in cost per reward unit without assigning future token value."),
    AirdropTarget("decibel-liquidity", "Decibel Liquidity Amps Agent", "READ_ONLY", "A", "https://docs.decibel.trade/rewards/amps", "https://docs.decibel.trade/", "amps", 2, "Liquidity analysis only; deposit/withdrawal remains human-gated."),
    AirdropTarget("grvt", "GRVT API Rewards Agent", "DRY_RUN", "S", "https://help.grvt.io/en/articles/12332040-live-rewards-season-2-0", "https://api-docs.grvt.io/", "points", 2, "Re-verify current season and API versus UI reward treatment."),
    AirdropTarget("reya-trading", "Reya RCP API Trading Agent", "DRY_RUN", "S", "https://docs.reya.xyz/reya-token/reya-chain-points-faqs", "https://docs.reya.xyz/", "RCP", 2, "Track direct cost per RCP; future token value remains unknown unless official."),
    AirdropTarget("reya-staking", "Reya Staking/RLP Points Agent", "READ_ONLY", "A", "https://docs.reya.xyz/reya-token/reya-chain-points-faqs", "https://docs.reya.xyz/", "RCP", 2, "Staking/RLP research; asset movement remains human-gated."),
    AirdropTarget("extended-trading", "Extended Trading Points Agent", "DRY_RUN", "A", "https://docs.extended.exchange/extended-resources/points", "https://api.docs.extended.exchange/", "points", 2, "Re-verify current chain, season and API version on each scheduled pass."),
    AirdropTarget("extended-liquidity", "Extended Liquidity/Vault Agent", "READ_ONLY", "A", "https://docs.extended.exchange/extended-resources/points", "https://docs.extended.exchange/", "points", 3, "Liquidity/vault monitor only; asset movement remains human-gated."),
    AirdropTarget("nado-trading", "Nado Trading Points Agent", "DRY_RUN", "S", "https://docs.nado.xyz/points", "https://docs.nado.xyz/developer-resources", "points", 2, "REST/WebSocket dry-run seed; no real orders."),
    AirdropTarget("nado-nlp", "Nado NLP Liquidity Agent", "READ_ONLY", "A", "https://docs.nado.xyz/points", "https://docs.nado.xyz/", "points", 3, "NLP liquidity monitor; deposit/redeem remains human-gated."),
    AirdropTarget("kyan", "Kyan MCP Krystals Agent", "DRY_RUN", "S", "https://blog.kyan.blue/p/development-update-referrals-rewards-hub-and-more", "https://docs.kyan.blue/docs/mcp", "Krystals", 1, "Wave 1. Kyan confirms Krystals and API/MCP separately; API-trading-to-Krystals equivalence still requires explicit official confirmation."),
    AirdropTarget("lighter", "Lighter API Points Trader", "DRY_RUN", "S", "https://docs.lighter.xyz/points-program", "https://apidocs.lighter.xyz/", "points", 1, "Wave 1. Current general Points Program and Retail pages describe ongoing weekly Season 2 distributions and organic UI/API trading; live financial execution remains approval-gated."),
    AirdropTarget("ethereal-trading", "Ethereal API Points Trader", "DRY_RUN", "S", "https://docs.ethereal.trade/points/ethereal-points", "https://docs.ethereal.trade/", "points", 2, "Authentic-trading simulation only; no artificial volume."),
    AirdropTarget("ethereal-margin", "Ethereal USDe/Margin Points Agent", "READ_ONLY", "A", "https://docs.ethereal.trade/points/ethereal-points", "https://docs.ethereal.trade/", "points", 3, "Margin/deposit monitor; approvals and asset movement remain human-gated."),
    AirdropTarget("exchange01", "01 Exchange Participation Agent", "DRY_RUN", "C", "https://docs.01.xyz/support/faq/general", "https://docs.01.xyz/", "participation", 3, "Low-confidence reward economics; treat monetary value as UNKNOWN."),
)


WAVE1_REWARD_VERIFICATION: dict[str, dict[str, object]] = {
    "pacifica": {
        "status": "CONFIRMED",
        "source": "https://pacifica.gitbook.io/docs/programs/points-program",
        "verified_at": "2026-08-11T05:55:47+09:00",
        "note": "Official Points Program states organic trading via GUI or API earns points; self-trading, Sybil and manipulative activity are excluded.",
    },
    "hibachi": {
        "status": "CONFIRMED",
        "source": "https://docs.hibachi.xyz/faq",
        "verified_at": "2026-08-11T05:55:47+09:00",
        "note": "Official FAQ states the points system is the same for UI and API trading; abusive activity can be disqualified.",
    },
    "kyan": {
        "status": "UNVERIFIED",
        "source": "https://blog.kyan.blue/p/development-update-referrals-rewards-hub-and-more",
        "verified_at": "2026-08-11T05:55:47+09:00",
        "note": "Official Kyan sources confirm Krystals from trading and API/MCP automation capability, but no explicit statement was found that API trading earns Krystals on the same basis.",
    },
    "lighter": {
        "status": "CONFIRMED",
        "source": "https://docs.lighter.xyz/points-program",
        "verified_at": "2026-08-12T09:25:35+00:00",
        "note": "Current official Points Program states Season 2 points are distributed every Friday and organic trading strategies via UI and API earn points; Sybil, self-trading and similar abusive activity are excluded.",
    },
}


WAVE1_PROGRAM_LIFECYCLE_VERIFICATION: dict[str, dict[str, object]] = {
    "pacifica": {
        "status": "ACTIVE",
        "sources": ["https://pacifica.gitbook.io/docs/programs/points-program"],
        "verified_at": "2026-08-11T05:55:47+09:00",
        "note": "Official Points Program describes current weekly snapshots and distributions.",
    },
    "hibachi": {
        "status": "ACTIVE",
        "sources": [
            "https://docs.hibachi.xyz/hibachi-rewards/hibachi-points",
            "https://docs.hibachi.xyz/faq",
        ],
        "verified_at": "2026-08-11T05:55:47+09:00",
        "note": "Official Hibachi docs describe recurring weekly points distributions and snapshots.",
    },
    "kyan": {
        "status": "REVERIFY",
        "sources": ["https://blog.kyan.blue/p/development-update-referrals-rewards-hub-and-more"],
        "verified_at": "2026-08-11T05:55:47+09:00",
        "note": "Rewards Hub and Krystals are documented, but this monitor does not treat the current reward program lifecycle as independently confirmed for API farming.",
    },
    "lighter": {
        "status": "ACTIVE",
        "sources": [
            "https://docs.lighter.xyz/points-program",
            "https://docs.lighter.xyz/points-program/retail",
            "https://docs.lighter.xyz/points-program/market-makers",
        ],
        "verified_at": "2026-08-12T09:25:35+00:00",
        "note": "Current general Points Program and Retail pages explicitly describe ongoing weekly Season 2 distributions. The Market Makers page's statement that Points Season 2 ended on 2025-12-26 is scoped to the market-maker track and does not override the current Retail/general program pages for organic retail/API trading.",
    },
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _probe_url(url: str | None, timeout: float = 6.0) -> dict[str, object]:
    if not url:
        return {"url": None, "ok": None, "status_code": None, "error": None}
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; crypto-auto-trade-airdrop-monitor/0.2; +https://github.com/univcorp2-ctrl/crypto-auto-trade)",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    }
    candidates = [url]
    if "?" not in url and not url.endswith("/"):
        candidates.append(f"{url}/")
    last_error: dict[str, object] | None = None
    for candidate in candidates:
        request = urllib.request.Request(candidate, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed seed URLs only
                return {"url": candidate, "ok": True, "status_code": response.status, "error": None}
        except urllib.error.HTTPError as exc:
            last_error = {"url": candidate, "ok": False, "status_code": exc.code, "error": f"HTTP {exc.code}"}
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            last_error = {"url": candidate, "ok": False, "status_code": None, "error": str(exc)[:200]}
    return last_error or {"url": url, "ok": False, "status_code": None, "error": "probe failed"}


def dry_run_target(target: AirdropTarget, *, probe_network: bool = True) -> dict[str, object]:
    program_probe = _probe_url(target.program_url) if probe_network else {"url": target.program_url, "ok": None, "status_code": None, "error": "network probe skipped"}
    api_probe = _probe_url(target.api_url) if probe_network else {"url": target.api_url, "ok": None, "status_code": None, "error": "network probe skipped"}
    reward_verification = WAVE1_REWARD_VERIFICATION.get(target.slug)
    lifecycle_verification = WAVE1_PROGRAM_LIFECYCLE_VERIFICATION.get(target.slug)
    reward_status = str(reward_verification["status"]) if reward_verification else "REVERIFY"
    lifecycle_status = str(lifecycle_verification["status"]) if lifecycle_verification else "REVERIFY"

    if lifecycle_status == "CONFLICT":
        status = "UNVERIFIED"
        blocked_reason = str(lifecycle_verification["note"])
    elif reward_status == "UNVERIFIED":
        status = "UNVERIFIED"
        blocked_reason = str(reward_verification["note"])
    elif program_probe["ok"] is False and reward_status != "CONFIRMED":
        status = "UNVERIFIED"
        blocked_reason = "Official program page was not reachable during this pass."
    elif target.mode == "READ_ONLY":
        status = "READ_ONLY"
        blocked_reason = "Asset movement is human-gated."
    else:
        status = "READY_DRY_RUN"
        if program_probe["ok"] is False and reward_status == "CONFIRMED" and lifecycle_status == "ACTIVE":
            blocked_reason = "DRY RUN allowed from separately verified official reward evidence; automated program-page reachability is currently degraded. LIVE remains disabled."
        else:
            blocked_reason = "LIVE disabled; legal/terms/reward eligibility require explicit re-verification before any live use."

    return {
        **asdict(target),
        "status": status,
        "program_probe": program_probe,
        "api_probe": api_probe,
        "api_reward_eligibility": reward_status,
        "reward_evidence_source": reward_verification["source"] if reward_verification else None,
        "reward_rule_verified_at": reward_verification["verified_at"] if reward_verification else None,
        "reward_evidence_note": reward_verification["note"] if reward_verification else None,
        "program_lifecycle_status": lifecycle_status,
        "program_lifecycle_sources": lifecycle_verification["sources"] if lifecycle_verification else [],
        "program_lifecycle_verified_at": lifecycle_verification["verified_at"] if lifecycle_verification else None,
        "program_lifecycle_note": lifecycle_verification["note"] if lifecycle_verification else None,
        "japan_legal_status": "LEGAL_REVIEW_REQUIRED",
        "live_approved": False,
        "points_before": None,
        "points_after": None,
        "estimated_total_cost_usd": None,
        "open_risk_usd": 0.0,
        "blocked_reason": blocked_reason,
        "checked_at": utc_now(),
    }


def run_all(*, probe_network: bool = True, targets: Iterable[AirdropTarget] = TARGETS) -> dict[str, object]:
    target_list = list(targets)
    if probe_network and target_list:
        worker_count = min(12, len(target_list))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(lambda target: dry_run_target(target, probe_network=True), target_list))
    else:
        results = [dry_run_target(target, probe_network=False) for target in target_list]
    return {
        "generated_at": utc_now(),
        "mode": "DRY_RUN",
        "live_approved": False,
        "target_count": len(results),
        "ready_dry_run": sum(item["status"] == "READY_DRY_RUN" for item in results),
        "read_only": sum(item["status"] == "READ_ONLY" for item in results),
        "unverified": sum(item["status"] == "UNVERIFIED" for item in results),
        "targets": results,
    }


def save_report(report: dict[str, object], output: Path = DEFAULT_OUTPUT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def load_latest(output: Path = DEFAULT_OUTPUT) -> dict[str, object]:
    if not output.exists():
        return run_all(probe_network=False)
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Airdrop agent dry-run and official-doc reachability monitor")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-network", action="store_true", help="Skip HTTP reachability checks")
    args = parser.parse_args()
    report = run_all(probe_network=not args.no_network)
    output = save_report(report, args.output)
    print(json.dumps({"ok": True, "output": str(output), **{key: report[key] for key in ("target_count", "ready_dry_run", "read_only", "unverified")}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
