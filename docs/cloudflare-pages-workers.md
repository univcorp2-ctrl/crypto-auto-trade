# Cloudflare 本番デプロイ（Workers + Static Assets）

FastAPI(Python) は Cloudflare Workers/Pages で直接は動かないため、ダッシュボードの
エンジン（指標・戦略・バックテスト・検証・勝てるか判定）を **TypeScript に移植**し、
**Cloudflare Workers（静的アセット同梱）** として常設デプロイします。これが
「Pages+Workers で常設」の実体です（静的フロント＋API を Cloudflare 内で完結）。

- ソース: [`worker/`](../worker)
- 静的ダッシュボード: 既存の [`static/`](../static) をそのまま配信（重複なし）
- API: `worker/src/index.ts` が `/api/*` を処理し、`/` と `/static/*` をアセットから配信
- エンジン: `worker/src/{indicators,strategies,backtest,validation,profitability,exchanges}.ts`
  は Python 実装の忠実移植で、サンプルデータ上で **バックテスト結果が6桁一致**することを
  `worker/test/engine.test.ts` で検証済み

## エンドポイント（Workers 上で動作）

`/api/health` `/api/strategies` `/api/exchanges` `/api/backtest` `/api/forward-test`
`/api/realtime` `/api/compare` `/api/validate` `/api/best-strategy`
`/api/verify-profitability`（勝てるか検証）`/api/market/prices`（CoinGecko 取得）

ライブ OHLCV は `data_source=live` のとき Binance 公開 API(klines) から取得を試み、
失敗時はサンプルにフォールバックします（Workers には ccxt が無いため）。
5年シミュレーションのファイル保存は Workers にファイルシステムが無いため非対応です。

## デプロイ手順

トークンは**絶対にコミット・直書きしません**。wrangler が環境変数から読み取ります。

```bash
# 1. 認証情報を環境変数に設定（シークレットとして。コマンド履歴/コミットに残さない）
export CLOUDFLARE_API_TOKEN=...          # Workers/Pages 編集権限のトークン
export CLOUDFLARE_ACCOUNT_ID=...         # Cloudflare のアカウントID

# 2. 依存導入・型チェック・パリティテスト・デプロイ
cd worker
npm install
./deploy.sh
```

デプロイ後、`https://crypto-auto-trade.<your-subdomain>.workers.dev` で公開されます。
独自ドメインに固定する場合は Cloudflare ダッシュボードまたは `wrangler.toml` の
`routes` で割り当ててください。

## ローカル確認

```bash
cd worker
npm install
npm test            # Python とのパリティテスト
npx wrangler dev    # http://127.0.0.1:8787
```

## 必要なトークン権限

このデプロイに必要なのは **Account > Workers Scripts: Edit**（および Workers の
静的アセットアップロード）です。提供トークンにこの権限が無い場合は、Cloudflare
ダッシュボードでスコープを付与した API トークンを発行してください。

## セキュリティ

- API トークンはコード／git に含めません。`worker/.gitignore` で `.dev.vars` 等も除外。
- 公開ダッシュボードには認証がありません。常設公開する場合は Cloudflare Access での
  保護を推奨します。
- 取引所の実取引はこの Worker には含まれません（バックテスト/検証のみ）。
