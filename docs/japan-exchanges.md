# Japan Exchange API Registry

This project keeps a Japan-focused exchange registry in `crypto_auto_trade/exchange_registry.py`.

## Research basis

- JVCEA first-class members: 32 members.
- JVCEA category split: all 32, crypto asset exchange business, crypto derivatives business, electronic payment instruments, funds transfer business.
- JVCEA statistics page reported 32 first-class members handling crypto assets as of 2026-06-04.
- FSA registration remains the final source for whether a business is legally registered.

## API-ready approach

The bot separates venues into statuses:

| status | meaning |
|---|---|
| `api_ready` | Public and private API documentation or known CCXT path is available. |
| `api_ready_candidate` | API likely exists, but venue/product/account differences must be verified before live trading. |
| `manual_review` | Registry entry exists, but no public trading API is assumed. |
| `derivatives_only_review` | Derivatives member; spot auto-trading is not assumed. |
| `not_exchange_trading` | Listed for completeness but not a spot crypto exchange trading target. |

## Implemented adapter readiness

| venue id | name | status | connector path |
|---|---|---|---|
| `bitflyer` | bitFlyer | `api_ready` | direct public ticker + CCXT candidate |
| `bitbank` | bitbank | `api_ready` | direct public ticker + CCXT candidate |
| `gmo_coin` | GMOコイン | `api_ready` | direct public ticker + private secrets metadata |
| `coincheck` | Coincheck | `api_ready` | direct public ticker + CCXT candidate |
| `binance_japan` | Binance Japan | `api_ready` | CCXT `binance` path, account/product availability must be checked |
| `zaif` | Zaif | `api_ready_candidate` | direct public ticker + CCXT candidate |
| `btcbox` | BTCBOX | `api_ready_candidate` | CCXT candidate |
| `gate_japan` | Gate Japan | `api_ready_candidate` | CCXT `gate` path, account/product availability must be checked |
| `okcoin_japan` | OKCoin Japan | `api_ready_candidate` | skeleton + secrets metadata |
| `bittrade` | BitTrade | `api_ready_candidate` | skeleton + secrets metadata |

## CLI

```bash
python -m crypto_auto_trade.cli list-exchanges
python -m crypto_auto_trade.cli list-api-ready-exchanges
python -m crypto_auto_trade.cli exchange-secrets --exchange bitflyer
python -m crypto_auto_trade.cli exchange-ticker --exchange bitflyer --symbol BTC_JPY
python -m crypto_auto_trade.cli exchange-ticker --exchange gmo_coin --symbol BTC_JPY
```

## Live trading note

Private trading remains blocked by the global live safety guard. The exchange registry prepares the adapter layer and secrets names, but it does not bypass:

```bash
CRYPTO_AUTO_TRADE_LIVE_ACK=I_UNDERSTAND_THIS_CAN_LOSE_MONEY
```

Do not enable withdrawals on API keys.
