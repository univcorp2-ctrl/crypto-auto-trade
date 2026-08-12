# AIRDROP Agent｜何をしているか・獲得までの流れ

## 結論

このAirdrop Agentは、単なる「案件監視」ではなく、毎回次の順で **獲得まで進める** ための定期処理です。

1. 公式Program / APIの到達性と現行ルールを確認
2. ポイント・報酬の獲得条件を判定
3. **無料・資金移動なし・wallet署名なし・実注文なし**で、公式に報酬対象と確認できたアクションがあれば自動実行
4. 実取引・入出金・Bridge・token approval・wallet署名が必要なら勝手に実行せず承認キューへ入れる
5. ルール未確認・公式資料競合なら停止
6. 実行結果、止まった理由、次に必要な操作をJSONへ保存

GitHub Actionsのスケジュールは毎時23分（UTC基準のcron `23 * * * *`）です。

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

トップには以下の集計があります。

- `auto_executed_action_count`: 実際に自動実行した安全な獲得アクション数
- `approval_required_count`: 実取引等のため承認待ちになった件数
- `blocked_unverified_count`: ルール未確認・競合で止めた件数
- `financial_actions_executed`: 自動で実行した金融アクション数（安全上0を維持）
- `asset_transfers_executed`: 自動資金移動数（0を維持）
- `wallet_signatures_executed`: 自動wallet署名数（0を維持）
- `live_orders_executed`: 自動LIVE注文数（0を維持）

## 現在のWave 1

| Target | 現状 | 獲得までの次工程 |
|---|---|---|
| Pacifica | Reward mechanics確認済み / Program ACTIVE | ポイント獲得は実取引が必要。上限付き取引案を承認キューへ |
| Hibachi | Reward mechanics確認済み / Program ACTIVE | ポイント獲得はexchange activityが必要。上限付き取引案を承認キューへ |
| Kyan | API取引→Krystalsの直接適格性未確認 | 公式根拠を再確認するまで停止 |
| Lighter | API points mechanicsは確認済みだが公式lifecycle記述が競合 | 矛盾解消まで停止 |

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
- 自動化が規約上許容される
- テストで副作用0を確認

現在のWave 1には、この条件を満たす実装済みアクションはありません。そのため「監視しているから獲得済み」とは表示せず、実取引が必要なものは承認待ちとして明示します。

## 禁止事項

- Sybil / multi-wallet farming
- self-trading / wash trading / circular volume
- market manipulation / fake liquidity / quote stuffing
- referral self-dealing
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
```

ネットワークアクセスなしの安全テスト:

```bash
python -m crypto_auto_trade.airdrop_acquisition --no-network
```

## 完了の意味

Airdrop Agentでは、次の3つを区別します。

- **監視成功**: 公式ページを確認できた
- **獲得準備成功**: 具体的な獲得アクションまで確定し、実行または承認キューへ入った
- **獲得成功**: 報酬/ポイント増加を実データで確認できた

監視成功だけを「獲得成功」とは扱いません。
