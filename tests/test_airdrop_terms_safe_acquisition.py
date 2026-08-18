from crypto_auto_trade import airdrop_agents
from crypto_auto_trade.airdrop_terms_safe_acquisition import (
    DECIBEL_TERMS_SOURCE,
    TERMS_AUTOMATION_BLOCKED_SLUGS,
    _apply_terms_guard_to_acquisition,
    _evaluate_target,
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
