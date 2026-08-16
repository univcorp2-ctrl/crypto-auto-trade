from crypto_auto_trade.airdrop_live_overrides import (
    STANDX_MAKER_EVIDENCE_SOURCE,
    STANDX_MAKER_LIVE_PARAMETERS,
)


def test_standx_spcx_current_live_maker_ceiling_is_one() -> None:
    """Current operator page is authoritative; re-check it before any economic action."""
    spcx = STANDX_MAKER_LIVE_PARAMETERS["pairs"]["SPCX-USD"]

    assert spcx["max_maker_hours_per_hour"] == 1
    assert spcx["session"] == "US equity session"
    assert STANDX_MAKER_EVIDENCE_SOURCE.endswith("/community-maker-yield")
