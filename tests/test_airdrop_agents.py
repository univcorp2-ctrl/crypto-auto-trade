import json

from crypto_auto_trade import airdrop_agents
from crypto_auto_trade.airdrop_agents import TARGETS, dry_run_target, load_latest, run_all


def _target(slug: str):
    return next(target for target in TARGETS if target.slug == slug)


def test_registry_has_twenty_unique_targets() -> None:
    assert len(TARGETS) == 20
    assert len({target.slug for target in TARGETS}) == 20


def test_wave_one_contains_expected_targets() -> None:
    wave_one = {target.slug for target in TARGETS if target.wave == 1}
    assert wave_one == {"pacifica", "hibachi", "kyan", "lighter"}


def test_dry_run_never_enables_live() -> None:
    result = dry_run_target(TARGETS[0], probe_network=False)
    assert result["live_approved"] is False
    assert result["japan_legal_status"] == "LEGAL_REVIEW_REQUIRED"


def test_verified_wave_one_api_reward_rules_are_recorded() -> None:
    for slug in ("pacifica", "hibachi", "lighter"):
        result = dry_run_target(_target(slug), probe_network=False)
        assert result["api_reward_eligibility"] == "CONFIRMED"
        assert result["program_lifecycle_status"] == "ACTIVE"
        assert result["reward_evidence_source"]
        assert result["reward_rule_verified_at"]
        assert result["status"] == "READY_DRY_RUN"


def test_kyan_reward_rule_is_confirmed_but_lifecycle_still_reverified_before_live_use() -> None:
    result = dry_run_target(_target("kyan"), probe_network=False)
    assert result["api_reward_eligibility"] == "CONFIRMED"
    assert result["program_lifecycle_status"] == "REVERIFY"
    assert result["status"] == "READY_DRY_RUN"
    assert "inference" in result["reward_evidence_note"].lower()
    assert result["live_approved"] is False


def test_lighter_scopes_old_market_maker_end_date_without_blocking_current_retail_program() -> None:
    result = dry_run_target(_target("lighter"), probe_network=False)
    assert result["api_reward_eligibility"] == "CONFIRMED"
    assert result["program_lifecycle_status"] == "ACTIVE"
    assert result["status"] == "READY_DRY_RUN"
    assert "market-maker track" in result["program_lifecycle_note"]
    assert result["live_approved"] is False


def test_exchange01_tracks_current_n1_og_badge_instead_of_legacy_points() -> None:
    result = dry_run_target(_target("exchange01"), probe_network=False)

    assert result["program_url"] == "https://hub.n1.xyz/"
    assert result["name"] == "N1 / 01 OG Badge Agent"
    assert result["api_reward_eligibility"] == "CONFIRMED"
    assert result["program_lifecycle_status"] == "ACTIVE"
    assert result["status"] == "READY_DRY_RUN"
    assert "01 OG badge" in result["reward_evidence_note"]
    assert "badge path" in result["program_lifecycle_note"]
    assert result["live_approved"] is False


def test_direct_decibel_dry_run_never_probes_network(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Decibel automated network probe must not run")

    monkeypatch.setattr(airdrop_agents, "_probe_url", fail_if_called)

    for slug in ("decibel-trading", "decibel-liquidity"):
        result = dry_run_target(_target(slug), probe_network=True)
        assert result["status"] == "UNVERIFIED"
        assert result["terms_automation_status"] == "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED"
        assert result["program_probe"]["ok"] is None
        assert "prohibit automated access" in result["blocked_reason"]


def test_run_all_is_dry_run_only_and_applies_current_guards() -> None:
    report = run_all(probe_network=False)
    assert report["mode"] == "DRY_RUN"
    assert report["live_approved"] is False
    assert report["target_count"] == 20
    assert report["terms_automation_blocked_count"] == 2
    assert report["ethereal_current_block_count"] == 2
    assert all(target["live_approved"] is False for target in report["targets"])

    ethereal = {
        item["slug"]: item
        for item in report["targets"]
        if item["slug"] in {"ethereal-trading", "ethereal-margin"}
    }
    assert all(item["status"] == "UNVERIFIED" for item in ethereal.values())
    assert all(item["reward_acquisition_state"] == "BLOCKED_UNVERIFIED" for item in ethereal.values())


def test_load_latest_reapplies_current_guards_to_stale_persisted_status(tmp_path) -> None:
    stale = run_all(probe_network=False)
    for item in stale["targets"]:
        if item["slug"] == "ethereal-trading":
            item["status"] = "READY_DRY_RUN"
            item.pop("current_evidence_status", None)
            item.pop("reward_acquisition_state", None)
        elif item["slug"] == "ethereal-margin":
            item["status"] = "READ_ONLY"
            item.pop("current_evidence_status", None)
            item.pop("reward_acquisition_state", None)
        elif item["slug"] in {"decibel-trading", "decibel-liquidity"}:
            item["status"] = "READY_DRY_RUN"
            item.pop("terms_automation_status", None)

    path = tmp_path / "latest.json"
    path.write_text(json.dumps(stale), encoding="utf-8")
    guarded = load_latest(path)

    ethereal = {
        item["slug"]: item
        for item in guarded["targets"]
        if item["slug"] in {"ethereal-trading", "ethereal-margin"}
    }
    decibel = {
        item["slug"]: item
        for item in guarded["targets"]
        if item["slug"] in {"decibel-trading", "decibel-liquidity"}
    }
    assert all(item["status"] == "UNVERIFIED" for item in ethereal.values())
    assert all(item["reward_acquisition_state"] == "BLOCKED_UNVERIFIED" for item in ethereal.values())
    assert all(item["status"] == "UNVERIFIED" for item in decibel.values())
    assert all(
        item["terms_automation_status"] == "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED"
        for item in decibel.values()
    )
