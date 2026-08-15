# AIRDROP Agent｜何をしているか・獲得までの流れ

## 結論

このAirdrop Agentは、単なる「案件監視」ではなく、毎回次の順で **獲得まで進める** ための定期処理です。

1. 公式Program / APIの到達性と現行ルールを確認
2. ポイント・報酬の獲得条件を判定
3. **無料・資金移動なし・wallet署名なし・実注文なし**で、公式に報酬対象と確認でき、実行経路とcredit条件まで確定したアクションがあれば自動実行
4. 非金融でも提出経路・account linkage・credit条件が未確定または裁量報酬なら、自動実行せず `additional_review_paths` へ分離
5. 実取引・入出金・Bridge・token approval・wallet署名が必要なら勝手に実行せず承認キューへ入れる
6. ルール未確認・公式資料競合なら停止
7. 実行結果、止まった理由、次に必要な操作をJSONへ保存

GitHub ActionsはUTC基準のcron `23,53 * * * *`で毎時23分と53分に起動機会を設けています。どちらのscheduled runでも `data/airdrop/latest.json` が35分未満なら重い獲得サイクルをskipします。35分以上なら実行することで、1回のcron取りこぼし後にstatusが90〜100分超古くなるリスクを下げつつ、不要な重複処理を抑えます。

## どこを見ればいいか

### 1. 状態確認

`data/airdrop/latest.json`

20候補について以下を保存します。

- Program/API到達性
- API経由の報酬適格性
- Program lifecycle
- Japan / Legal状態
- DRY RUN可否

### 2. 獲得作業の結果

`data/airdrop/acquisition-latest.json`

ここが今後の主画面です。各案件について以下を保存します。

- `acquisition_state`
- `action_taken`
- `auto_executed`
- `requires_user_approval`
- `requires_funds`
- `requires_wallet_signature`
- `next_action`
- `reason`

金融承認キューとは別に、無資金・無注文・無署名でも現行の提出/認証/credit条件が未確定な経路は `additional_review_paths` へ保存します。これは「安全だから実行済み」という意味ではありません。

トップには以下の集計があります。

- `auto_executed_action_count`: 実際に自動実行した安全な獲得アクション数
- `approval_required_count`: 実取引等のため承認待ちになった件数
- `nonfinancial_review_required_count`: 金融操作不要だが提出経路・認証・credit条件等の追加確認が必要な報酬経路数
- `blocked_unverified_count`: ルール未確認・競合で止めた件数
- `financial_actions_executed`: 自動で実行した金融アクション数（安全上0を維持）
- `asset_transfers_executed`: 自動資金移動数（0を維持）
- `wallet_signatures_executed`: 自動wallet署名数（0を維持）
- `live_orders_executed`: 自動LIVE注文数（0を維持）

## 現在のWave 1

2026-08-15時点のリポジトリ判定です。`READY_DRY_RUN`や`CONFIRMED`はLIVE実行許可を意味しません。全件 `LEGAL_REVIEW_REQUIRED` / `live_approved=false` を維持します。

| Target | 現状 | 獲得までの次工程 |
|---|---|---|
| Pacifica | Reward mechanics `CONFIRMED` / Program `ACTIVE`。公式Program/API到達確認済み | ポイント獲得は実取引が必要。現行Terms・日本居住者適格性・口座条件を再確認後、上限付き実取引案を明示承認キューへ |
| Hibachi | Reward mechanics `CONFIRMED` / Program `ACTIVE`。UI/APIのpoints算定同一を公式FAQで確認済み | exchange activityが必要。現行Terms・日本居住者適格性・口座条件を再確認後、上限付き実取引案を明示承認キューへ |
| Kyan | Repo上Reward mechanics `CONFIRMED`だが、API取引→Krystalsは公式一次資料を組み合わせた `PRIMARY_DOCS_CHANNEL_NEUTRAL_INFERENCE`。Program lifecycleは `REVERIFY` | 現行Krystals lifecycle、Terms/管轄、口座/API key、EIP-712署名条件を再確認し、上限付きAPI取引案を明示承認キューへ。署名・実注文は自動実行しない |
| Lighter | Reward mechanics `CONFIRMED` / Retail・general pathは `ACTIVE`。一般/RetailはSeason 2週次配布とUI/API取引を記載。Market Makersページの2025-12-26終了記載はMM trackとして分離 | 現行Terms・口座適格性・live Retail points条件を実行直前に再確認後、上限付きorganic API取引案を明示承認キューへ |

## 非金融だが未実行の報酬経路

### Reya RCP Signal

Reyaの現行公式RCP FAQは、**Signal** をRCP獲得カテゴリとして挙げ、trading/stakingを行わなくても、Reyaの成長に寄与する高シグナルなcode・content・connectionsでRCPを得られると説明しています。ただしSignalは裁量的で、今回確認できた公式資料では現行の提出/認識チャネル、account linkage、確定credit条件を特定できていません。

そのため `reya-signal` は `NONFINANCIAL_REWARD_PATH_REVIEW_REQUIRED` として `additional_review_paths` に保存します。資金移動・注文・wallet署名は不要な候補ですが、**自動投稿・spam・manufactured engagement・referral self-dealingは行わず**、公式提出経路とaccount linkageが確認できるまで実行しません。

## 自動実行の安全条件

`SAFE_AUTO_ACTIONS`へ登録できるのは、以下を全部満たすものだけです。

- 入金・出金なし
- Bridgeなし
- token approvalなし
- value transferなし
- wallet署名なし
- private key / seed phrase不要
- 実注文・経済的ポジションなし
- 現行公式ルールで報酬対象と明記
- 現行の実行/提出経路とaccount linkageが確認済み
- reward/credit条件を実行後に検証できる
- 自動化が規約上許容される
- テストで副作用0を確認

現在、この条件をすべて満たす実装済みアクションはありません。そのため「監視しているから獲得済み」「非金融だから獲得済み」とは表示しません。

## 禁止事項

- Sybil / multi-wallet farming
- self-trading / wash trading / circular volume
- market manipulation / fake liquidity / quote stuffing
- referral self-dealing
- spam / manufactured engagement / fake community contribution
- VPN・device fingerprint等による規制・bot検知回避
- secret / private key / seed phraseのcommitやログ出力

## 手動実行

状態確認だけ:

```bash
python -m crypto_auto_trade.airdrop_agents --output data/airdrop/latest.json
```

獲得サイクル:

```bash
python -m crypto_auto_trade.airdrop_acquisition \
  --status-output data/airdrop/latest.json \
  --output data/airdrop/acquisition-latest.json
python -m crypto_auto_trade.airdrop_live_overrides \
  --input data/airdrop/acquisition-latest.json \
  --output data/airdrop/acquisition-latest.json
```

ネットワークアクセスなしの安全テスト:

```bash
python -m crypto_auto_trade.airdrop_acquisition --no-network
```

## 完了の意味

Airdrop Agentでは、次の4つを区別します。

- **監視成功**: 公式ページを確認できた
- **獲得経路確認**: 報酬対象行動は確認できたが、提出/認証/credit条件等が残っている
- **獲得準備成功**: 具体的な獲得アクションまで確定し、実行または承認キューへ入った
- **獲得成功**: 報酬/ポイント増加を実データで確認できた

監視成功や獲得経路確認だけを「獲得成功」とは扱いません。

## 調査実行が無効になった場合の保護

報酬経路の昇格判断に使う調査が、検索上限・直列実行・必須一次情報確認などの現行調査ルールに違反した場合、その実行内では新しい `VERIFIED_GATED_ACTIONS` や承認キュー昇格を本番確定しません。

- 既存の安全な本番状態へ戻す
- 実注文・資金移動・署名は当然実行しない
- 取得済みの公式URLは次回の再検証用として保持する
- 次回は既知URLの直接取得から再開し、クリーンな実行でのみ昇格を確定する
- 調査ルール違反を「証拠内容が正しそうだから」で無視しない

これにより、証拠そのものが有望でも、無効な調査手順から本番状態が確定されることを防ぎます。
