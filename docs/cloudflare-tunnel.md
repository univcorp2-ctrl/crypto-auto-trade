# Cloudflare Tunnel で公開する

`crypto_auto_trade.web` は FastAPI (Python) なので、Cloudflare Workers/Pages
では**そのままは動きません**。ローカルで起動した FastAPI を **Cloudflare Tunnel
(`cloudflared`)** 経由で公開するのが最小構成です。コードはほぼそのまま、
HTTPS の公開 URL が手に入ります。

## 仕組み

```
ブラウザ ──HTTPS──> Cloudflare Edge ──Tunnel──> cloudflared ──HTTP──> 127.0.0.1:8000 (FastAPI)
```

- アプリは `127.0.0.1` にしか bind しないため、ポートを直接インターネットに
  開けません（Cloudflare 側で TLS 終端・DDoS 緩和を担当）。
- 「クイックトンネル」を使えば Cloudflare アカウント不要で、
  `https://<ランダム>.trycloudflare.com` の一時 URL が払い出されます。

## 1. 前提

```bash
pip install -e '.[web]'
# cloudflared を導入:
# https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
```

## 2. 起動（クイックトンネル）

```bash
scripts/cloudflare_tunnel.sh
```

スクリプトは次を行います。

1. `python -m crypto_auto_trade.web` で FastAPI を `127.0.0.1:8000` に起動。
2. `/api/health` が応答するまで待機。
3. `cloudflared tunnel --url http://127.0.0.1:8000` を実行し、公開 URL を表示。

出力されたログ中の `https://<...>.trycloudflare.com` を開くとダッシュボードが
表示されます。

ポート変更:

```bash
PORT=8001 scripts/cloudflare_tunnel.sh
```

## 3. 常設の独自ドメイン（任意）

無料アカウントで独自ドメインに固定したい場合は名前付きトンネルを使います。

```bash
cloudflared tunnel login
cloudflared tunnel create crypto-auto-trade
cloudflared tunnel route dns crypto-auto-trade trade.example.com
TUNNEL_NAME=crypto-auto-trade scripts/cloudflare_tunnel.sh
```

## 4. 公開時の注意

- このダッシュボードには認証がありません。公開 URL を知る誰でもバックテストや
  シミュレーションを実行できます。常設公開する場合は Cloudflare Access 等で
  保護してください。
- ライブ取引は環境変数 (`EXCHANGE_API_KEY` / `EXCHANGE_API_SECRET` /
  `CRYPTO_AUTO_TRADE_LIVE_ACK`) が揃わない限りロックされたままです。
  公開ホストにはこれらの値を置かないでください。
- 取引所の API キーは出金無効で発行してください。

## 5. 「勝てるか検証」をブラウザから

公開後、ダッシュボードの **「勝てるか検証」** ボタン
（`GET /api/verify-profitability`）で、登録済み全戦略バリエーションの
収益性 verdict（`win_likely` / `marginal` / `lose_likely`）を確認できます。
これは過去データ・サンプルに基づく判定であり、将来の利益を保証するもの
ではありません。
