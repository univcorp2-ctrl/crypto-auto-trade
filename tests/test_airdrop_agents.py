from crypto_auto_trade.airdrop_agents import TARGETS, dry_run_target, run_all


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
    assert result["api_reward_eligibility"] == "REVERIFY"


def test_run_all_is_dry_run_only() -> None:
    report = run_all(probe_network=False)
    assert report["mode"] == "DRY_RUN"
    assert report["live_approved"] is False
    assert report["target_count"] == 20
    assert all(target["live_approved"] is False for target in report["targets"])
