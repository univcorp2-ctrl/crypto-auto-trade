from crypto_auto_trade.airdrop_decibel_claim_surface import (
    DECIBEL_LIVE_CAMPAIGNS_SOURCE,
    _fetch_url,
    fetch_decibel_claim_sources,
)


def test_direct_decibel_fetch_is_blocked_by_terms_guard() -> None:
    try:
        _fetch_url(DECIBEL_LIVE_CAMPAIGNS_SOURCE)
    except RuntimeError as exc:
        assert str(exc) == "AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED"
    else:
        raise AssertionError("Decibel automated fetch unexpectedly executed")


def test_decibel_fetch_collection_returns_fail_closed_errors_only() -> None:
    sources, errors = fetch_decibel_claim_sources()
    assert sources == {}
    assert errors
    assert set(errors.values()) == {"AUTOMATED_ACCESS_PROHIBITED_FAIL_CLOSED"}
