from datetime import UTC, datetime, timedelta

from crypto_auto_trade import airdrop_agents
from crypto_auto_trade.airdrop_ethereal_current import ETHEREAL_VERIFIED_AT, TTL_DAYS
from crypto_auto_trade.airdrop_terms_safe_acquisition import (
    DECIBEL_TERMS_SOURCE,
    TERMS_AUTOMATION_BLOCKED_SLUGS,
    _apply_ethereal_guard_to_status,
    _apply_terms_guard_to_acquisition,
    _evaluate_target,
    run_terms_safe_status,
)


def _target(slug: str):
    return next(target for target in airdrop_agents.TARGETS if target.slug == slug)


def test_decibel_targets_do_not_probe_network(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Decibel automated network probe must not run")

    monkeypatch.setattr(airdrop_agents, "_probe_url", fail_if_called)

    for slug in TERMS_AUTOMATION_BLOCKED_SLUGS:
        result = _evaluate_target(_target(slug))
        assert result["status"] == "UNVERIFIED"
        assert result["terms_automation_status"] == "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED"
        assert result["terms_evidence_source"] == DECIBEL_TERMS_SOURCE
        assert result["program_probe"]["ok"] is None
        assert "prohibit automated access" in result["blocked_reason"]


def test_terms_guard_marks_decibel_actions_blocked_and_recounts_approvals() -> None:
    report = {
        "actions": [
            {"slug": "decibel-trading", "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL"},
            {"slug": "decibel-liquidity", "acquisition_state": "APPROVAL_REQUIRED_ASSET_MOVE"},
            {"slug": "pacifica", "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL"},
        ],
        "additional_approval_paths": [
            {"slug": "manual-other", "acquisition_state": "APPROVAL_REQUIRED_FINANCIAL"}
        ],
        "blocked_unverified_count": 0,
        "reverify_required_count": 0,
        "primary_approval_required_count": 3,
        "additional_approval_required_count": 1,
        "approval_required_count": 4,
    }

    updated = _apply_terms_guard_to_acquisition(report)
    decibel = [action for action in updated["actions"] if action["slug"].startswith("decibel-")]

    assert updated["terms_automation_blocked_count"] == 2
    assert updated["blocked_unverified_count"] == 2
    assert updated["primary_approval_required_count"] == 1
    assert updated["additional_approval_required_count"] == 1
    assert updated["approval_required_count"] == 2
    assert all(action["acquisition_state"] == "BLOCKED_UNVERIFIED" for action in decibel)
    assert all(action["automation_permitted"] is False for action in decibel)
    assert all("human/manual" in action["next_action"] for action in decibel)
    assert updated["actions"][2]["acquisition_state"] == "APPROVAL_REQUIRED_FINANCIAL"


def test_terms_safe_status_propagates_ethereal_fail_closed_state() -> None:
    result = run_terms_safe_status(probe_network=False)
    ethereal = {
        item["slug"]: item
        for item in result["targets"]
        if item["slug"] in {"ethereal-trading", "ethereal-margin"}
    }

    assert result["ethereal_current_block_count"] == 2
    assert set(ethereal) == {"ethereal-trading", "ethereal-margin"}
    assert all(item["status"] == "UNVERIFIED" for item in ethereal.values())
    assert all(item["reward_acquisition_state"] == "BLOCKED_UNVERIFIED" for item in ethereal.values())
    assert all("FAIL_CLOSED" in item["current_evidence_status"] for item in ethereal.values())
    assert result["unverified"] >= 4


def test_ethereal_status_stays_fail_closed_after_evidence_ttl() -> None:
    verified = datetime.fromisoformat(ETHEREAL_VERIFIED_AT).astimezone(UTC)
    report = {
        "ready_dry_run": 1,
        "read_only": 1,
        "unverified": 0,
        "targets": [
            {"slug": "ethereal-trading", "status": "READY_DRY_RUN"},
            {"slug": "ethereal-margin", "status": "READ_ONLY"},
        ],
    }

    result = _apply_ethereal_guard_to_status(
        report,
        now=verified + timedelta(days=TTL_DAYS, seconds=1),
    )

    assert result["ethereal_current_block_count"] == 2
    assert result["ready_dry_run"] == 0
    assert result["read_only"] == 0
    assert result["unverified"] == 2
    assert all(item["status"] == "UNVERIFIED" for item in result["targets"])
    assert all(
        item["current_evidence_status"] == "PRIMARY_EVIDENCE_EXPIRED_REVERIFY_FAIL_CLOSED"
        for item in result["targets"]
    )
