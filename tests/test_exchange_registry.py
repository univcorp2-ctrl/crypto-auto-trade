from crypto_auto_trade.exchange_adapters import build_private_client, build_public_client
from crypto_auto_trade.exchange_registry import api_ready_venues, get_exchange_venue, list_exchange_venues


def test_japan_exchange_registry_has_jvcea_first_class_members() -> None:
    venues = list_exchange_venues()
    assert len(venues) == 32
    assert get_exchange_venue("bitflyer").api_status == "api_ready"
    assert get_exchange_venue("gmo_coin").public_api is True


def test_api_ready_venues_exist() -> None:
    ids = {venue.id for venue in api_ready_venues()}
    assert "bitflyer" in ids
    assert "gmo_coin" in ids
    assert "coincheck" in ids


def test_exchange_clients_prepare_without_network_call() -> None:
    public_client = build_public_client("bitflyer")
    private_client = build_private_client("bitflyer")
    assert public_client.venue.id == "bitflyer"
    secrets = private_client.explain_required_secrets()
    assert "BITFLYER_API_KEY" in secrets["required_secrets"]
