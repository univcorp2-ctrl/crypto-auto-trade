// Compact port of the Japan exchange registry (crypto_auto_trade/exchange_registry.py).
export interface Venue {
  id: string;
  name: string;
  jvcea_member_no: string;
  api_status: string;
  ccxt_id: string | null;
  default_symbol: string;
}

export const VENUES: Venue[] = [
  { id: "moneypartners", name: "株式会社マネーパートナーズ", jvcea_member_no: "1001", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "bitflyer", name: "株式会社bitFlyer", jvcea_member_no: "1002", api_status: "api_ready", ccxt_id: "bitflyer", default_symbol: "BTC_JPY" },
  { id: "custodiem", name: "株式会社 Custodiem", jvcea_member_no: "1003", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "bitbank", name: "ビットバンク株式会社", jvcea_member_no: "1004", api_status: "api_ready", ccxt_id: "bitbank", default_symbol: "btc_jpy" },
  { id: "gmo_coin", name: "GMOコイン株式会社", jvcea_member_no: "1006", api_status: "api_ready", ccxt_id: null, default_symbol: "BTC_JPY" },
  { id: "bittrade", name: "ビットトレード株式会社", jvcea_member_no: "1007", api_status: "api_ready_candidate", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "btcbox", name: "BTCボックス株式会社", jvcea_member_no: "1008", api_status: "api_ready_candidate", ccxt_id: "btcbox", default_symbol: "BTC/JPY" },
  { id: "sbi_vc_trade", name: "SBI VCトレード株式会社", jvcea_member_no: "1011", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "finx_jcrypto", name: "FINX JCrypto株式会社", jvcea_member_no: "1012", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "coinhub", name: "COINHUB株式会社", jvcea_member_no: "1013", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "zaif", name: "株式会社Zaif", jvcea_member_no: "1014", api_status: "api_ready_candidate", ccxt_id: "zaif", default_symbol: "btc_jpy" },
  { id: "binance_japan", name: "Binance Japan株式会社", jvcea_member_no: "1016", api_status: "api_ready", ccxt_id: "binance", default_symbol: "BTC/JPY" },
  { id: "coincheck", name: "コインチェック株式会社", jvcea_member_no: "1017", api_status: "api_ready", ccxt_id: "coincheck", default_symbol: "btc_jpy" },
  { id: "rakuten_wallet", name: "楽天ウォレット株式会社", jvcea_member_no: "1018", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "sblox", name: "S.BLOX株式会社", jvcea_member_no: "1019", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "gate_japan", name: "Gate Japan株式会社", jvcea_member_no: "1021", api_status: "api_ready_candidate", ccxt_id: "gate", default_symbol: "BTC/JPY" },
  { id: "okcoin_japan", name: "オーケーコイン・ジャパン株式会社", jvcea_member_no: "1023", api_status: "api_ready_candidate", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "monex", name: "マネックス証券株式会社", jvcea_member_no: "1024", api_status: "derivatives_only_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "sbi_fx_trade", name: "SBI FXトレード株式会社", jvcea_member_no: "1026", api_status: "derivatives_only_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "osl_japan", name: "OSL Japan株式会社", jvcea_member_no: "1028", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "digital_asset_markets", name: "株式会社デジタルアセットマーケッツ", jvcea_member_no: "1029", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "mercury_cointrade", name: "株式会社マーキュリー", jvcea_member_no: "1030", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "backseat", name: "BACKSEAT暗号資産交換業株式会社", jvcea_member_no: "1031", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "hashkey_japan", name: "HashKey Japan株式会社", jvcea_member_no: "1032", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "gaia", name: "株式会社ガイア", jvcea_member_no: "1034", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "crypto_garage", name: "株式会社Crypto Garage", jvcea_member_no: "1035", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "traderssec", name: "トレイダーズ証券株式会社", jvcea_member_no: "1037", api_status: "derivatives_only_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "mercoin", name: "株式会社メルコイン", jvcea_member_no: "1039", api_status: "manual_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "goldenway_japan", name: "ゴールデンウェイ・ジャパン株式会社", jvcea_member_no: "1040", api_status: "derivatives_only_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "sbi_securities", name: "株式会社SBI証券", jvcea_member_no: "1041", api_status: "derivatives_only_review", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "jpyc", name: "JPYC株式会社", jvcea_member_no: "1042", api_status: "not_exchange_trading", ccxt_id: null, default_symbol: "BTC/JPY" },
  { id: "dmm_securities", name: "株式会社DMM.com証券", jvcea_member_no: "1043", api_status: "derivatives_only_review", ccxt_id: null, default_symbol: "BTC/JPY" },
];

export function apiReadyVenues(): Venue[] {
  return VENUES.filter((v) => v.api_status === "api_ready" || v.api_status === "api_ready_candidate");
}
