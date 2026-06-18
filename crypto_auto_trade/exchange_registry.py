from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExchangeVenue:
    id: str
    name: str
    jvcea_member_no: str
    business_types: tuple[str, ...]
    api_status: str
    public_api: bool
    private_api: bool
    ccxt_id: str | None = None
    api_doc_url: str | None = None
    ticker_url_template: str | None = None
    default_symbol: str = "BTC/JPY"
    required_secrets: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""


JAPAN_EXCHANGES: dict[str, ExchangeVenue] = {
    "moneypartners": ExchangeVenue("moneypartners", "株式会社マネーパートナーズ", "1001", ("暗号資産交換業", "暗号資産デリバティブ取引業"), "manual_review", False, False, notes="API公開状況は手動確認対象"),
    "bitflyer": ExchangeVenue("bitflyer", "株式会社bitFlyer", "1002", ("暗号資産交換業", "暗号資産デリバティブ取引業"), "api_ready", True, True, "bitflyer", "https://lightning.bitflyer.com/docs", "https://api.bitflyer.com/v1/ticker?product_code={symbol}", "BTC_JPY", ("BITFLYER_API_KEY", "BITFLYER_API_SECRET"), "HTTP API and Realtime API"),
    "custodiem": ExchangeVenue("custodiem", "株式会社 Custodiem", "1003", ("暗号資産交換業", "暗号資産デリバティブ取引業"), "manual_review", False, False, notes="カストディ色が強く売買APIは手動確認対象"),
    "bitbank": ExchangeVenue("bitbank", "ビットバンク株式会社", "1004", ("暗号資産交換業",), "api_ready", True, True, "bitbank", "https://github.com/bitbankinc/bitbank-api-docs", "https://public.bitbank.cc/{symbol}/ticker", "btc_jpy", ("BITBANK_API_KEY", "BITBANK_API_SECRET"), "Public ticker and private trading API known"),
    "gmo_coin": ExchangeVenue("gmo_coin", "GMOコイン株式会社", "1006", ("暗号資産交換業", "暗号資産デリバティブ取引業"), "api_ready", True, True, None, "https://api.coin.z.com/docs/", "https://api.coin.z.com/public/v1/ticker?symbol={symbol}", "BTC_JPY", ("GMO_COIN_API_KEY", "GMO_COIN_API_SECRET"), "Public API and Private API documented"),
    "bittrade": ExchangeVenue("bittrade", "ビットトレード株式会社", "1007", ("暗号資産交換業", "暗号資産デリバティブ取引業"), "api_ready_candidate", True, True, None, "https://www.bittrade.co.jp/ja-jp/api/", None, "BTC/JPY", ("BITTRADE_API_KEY", "BITTRADE_API_SECRET"), "API is venue-specific; adapter skeleton included"),
    "btcbox": ExchangeVenue("btcbox", "BTCボックス株式会社", "1008", ("暗号資産交換業",), "api_ready_candidate", True, True, "btcbox", "https://www.btcbox.co.jp/help/asm", None, "BTC/JPY", ("BTCBOX_API_KEY", "BTCBOX_API_SECRET"), "CCXT may support public/private depending on installed version"),
    "sbi_vc_trade": ExchangeVenue("sbi_vc_trade", "SBI VCトレード株式会社", "1011", ("暗号資産交換業", "暗号資産デリバティブ取引業", "電子決済手段等取引業"), "manual_review", False, False, notes="一般公開売買APIは手動確認対象"),
    "finx_jcrypto": ExchangeVenue("finx_jcrypto", "FINX JCrypto株式会社", "1012", ("暗号資産交換業",), "manual_review", False, False),
    "coinhub": ExchangeVenue("coinhub", "COINHUB株式会社", "1013", ("暗号資産交換業",), "manual_review", False, False),
    "zaif": ExchangeVenue("zaif", "株式会社Zaif", "1014", ("暗号資産交換業",), "api_ready_candidate", True, True, "zaif", "https://zaif-api-document.readthedocs.io/", "https://api.zaif.jp/api/1/ticker/{symbol}", "btc_jpy", ("ZAIF_API_KEY", "ZAIF_API_SECRET"), "Public ticker template included"),
    "binance_japan": ExchangeVenue("binance_japan", "Binance Japan株式会社", "1016", ("暗号資産交換業",), "api_ready", True, True, "binance", "https://developers.binance.com/docs/binance-spot-api-docs", None, "BTC/JPY", ("BINANCE_API_KEY", "BINANCE_API_SECRET"), "Use CCXT binance adapter; Japan account/product availability must be checked"),
    "coincheck": ExchangeVenue("coincheck", "コインチェック株式会社", "1017", ("暗号資産交換業",), "api_ready", True, True, "coincheck", "https://coincheck.com/ja/documents/exchange/api", "https://coincheck.com/api/ticker?pair={symbol}", "btc_jpy", ("COINCHECK_API_KEY", "COINCHECK_API_SECRET"), "Public ticker and private order API known"),
    "rakuten_wallet": ExchangeVenue("rakuten_wallet", "楽天ウォレット株式会社", "1018", ("暗号資産交換業", "暗号資産デリバティブ取引業"), "manual_review", False, False),
    "sblox": ExchangeVenue("sblox", "S.BLOX株式会社", "1019", ("暗号資産交換業",), "manual_review", False, False),
    "gate_japan": ExchangeVenue("gate_japan", "Gate Japan株式会社", "1021", ("暗号資産交換業",), "api_ready_candidate", True, True, "gate", "https://www.gate.com/docs/developers/apiv4/", None, "BTC/JPY", ("GATE_API_KEY", "GATE_API_SECRET"), "Use CCXT gate if account/product supports Japan venue"),
    "okcoin_japan": ExchangeVenue("okcoin_japan", "オーケーコイン・ジャパン株式会社", "1023", ("暗号資産交換業",), "api_ready_candidate", True, True, None, "https://www.okcoin.jp/api", None, "BTC/JPY", ("OKCOIN_JP_API_KEY", "OKCOIN_JP_API_SECRET", "OKCOIN_JP_PASSPHRASE")),
    "monex": ExchangeVenue("monex", "マネックス証券株式会社", "1024", ("暗号資産デリバティブ取引業",), "derivatives_only_review", False, False),
    "sbi_fx_trade": ExchangeVenue("sbi_fx_trade", "SBI FXトレード株式会社", "1026", ("暗号資産デリバティブ取引業",), "derivatives_only_review", False, False),
    "osl_japan": ExchangeVenue("osl_japan", "OSL Japan株式会社", "1028", ("暗号資産交換業",), "manual_review", False, False),
    "digital_asset_markets": ExchangeVenue("digital_asset_markets", "株式会社デジタルアセットマーケッツ", "1029", ("暗号資産交換業",), "manual_review", False, False),
    "mercury_cointrade": ExchangeVenue("mercury_cointrade", "株式会社マーキュリー", "1030", ("暗号資産交換業",), "manual_review", False, False),
    "backseat": ExchangeVenue("backseat", "BACKSEAT暗号資産交換業株式会社", "1031", ("暗号資産交換業",), "manual_review", False, False),
    "hashkey_japan": ExchangeVenue("hashkey_japan", "HashKey Japan株式会社", "1032", ("暗号資産交換業",), "manual_review", False, False),
    "gaia": ExchangeVenue("gaia", "株式会社ガイア", "1034", ("暗号資産交換業",), "manual_review", False, False),
    "crypto_garage": ExchangeVenue("crypto_garage", "株式会社Crypto Garage", "1035", ("暗号資産交換業",), "manual_review", False, False),
    "traderssec": ExchangeVenue("traderssec", "トレイダーズ証券株式会社", "1037", ("暗号資産デリバティブ取引業",), "derivatives_only_review", False, False),
    "mercoin": ExchangeVenue("mercoin", "株式会社メルコイン", "1039", ("暗号資産交換業",), "manual_review", False, False),
    "goldenway_japan": ExchangeVenue("goldenway_japan", "ゴールデンウェイ・ジャパン株式会社", "1040", ("暗号資産デリバティブ取引業",), "derivatives_only_review", False, False),
    "sbi_securities": ExchangeVenue("sbi_securities", "株式会社SBI証券", "1041", ("暗号資産デリバティブ取引業",), "derivatives_only_review", False, False),
    "jpyc": ExchangeVenue("jpyc", "JPYC株式会社", "1042", ("資金移動業",), "not_exchange_trading", False, False),
    "dmm_securities": ExchangeVenue("dmm_securities", "株式会社DMM.com証券", "1043", ("暗号資産デリバティブ取引業",), "derivatives_only_review", False, False),
}


def list_exchange_venues() -> list[ExchangeVenue]:
    return list(JAPAN_EXCHANGES.values())


def api_ready_venues() -> list[ExchangeVenue]:
    return [venue for venue in JAPAN_EXCHANGES.values() if venue.api_status in {"api_ready", "api_ready_candidate"}]


def get_exchange_venue(exchange_id: str) -> ExchangeVenue:
    if exchange_id not in JAPAN_EXCHANGES:
        raise ValueError(f"unknown exchange id: {exchange_id}")
    return JAPAN_EXCHANGES[exchange_id]
