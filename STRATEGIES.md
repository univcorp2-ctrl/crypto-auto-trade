# Strategy Index / 戦略一覧

このリポジトリの戦略はここにあります。

## 実装ファイル

| 目的 | ファイル |
|---|---|
| 5つの基本戦略本体 | `crypto_auto_trade/strategies.py` |
| 100種類以上の戦略バリエーション定義 | `crypto_auto_trade/strategy_variants.py` |
| バックテスト・必須トレーリングストップ | `crypto_auto_trade/backtest.py` |
| 300回検証・Best候補選定 | `crypto_auto_trade/validation.py` |
| CLIから戦略を呼ぶ入口 | `crypto_auto_trade/cli.py` |
| 画面/APIから戦略を呼ぶ入口 | `crypto_auto_trade/web.py` |

## 5つの基本戦略

### 1. `regime_guard`
相場を **trend / range / shock** に分けて判断する初期推奨戦略です。

見るもの:

- EMA: 方向確認
- Donchian: 高値ブレイク確認
- ATR: 急変・ショック回避
- z-score: レンジ内の行き過ぎ判定
- range efficiency: 値動きの素直さ

特徴:

- 混合相場向け
- 保守的
- BUY後は必ずトレーリングストップ

### 2. `ema_cross`
短期EMAが長期EMAを上回ったら買う、シンプルな順張りです。

特徴:

- トレンド相場向け
- 分かりやすい
- レンジでは弱い
- BUY後は必ずトレーリングストップ

### 3. `donchian_trend`
過去高値を抜けたら買う、ブレイクアウト戦略です。

特徴:

- 強い上昇・高値更新相場向け
- フェイクブレイクに弱い
- BUY後は必ずトレーリングストップ

### 4. `rsi_reversion`
売られすぎを拾い、戻ったら逃げる平均回帰戦略です。

特徴:

- レンジ相場向け
- 強い下落トレンドでは危険
- BUY後は必ずトレーリングストップ

### 5. `bollinger_breakout`
ボリンジャーバンド上抜けでボラティリティ拡大に乗る戦略です。

特徴:

- ボラ拡大局面向け
- 上ヒゲ反落に弱い
- BUY後は必ずトレーリングストップ

## 100種類以上のバリエーション

`crypto_auto_trade/strategy_variants.py` で、以下のようにパラメータ違いを大量生成しています。

| ファミリー | バリエーション数 | 例 |
|---|---:|---|
| `regime_guard` | 18 | `regime_guard_s80_b55_atr8` |
| `ema_cross` | 24 | `ema_cross_f5_s34` |
| `donchian_trend` | 24 | `donchian_l55_p100` |
| `rsi_reversion` | 24 | `rsi_rev_e30_x50_p50` |
| `bollinger_breakout` | 24 | `bollinger_w20_m2p0_p75` |

合計: 100種類以上。

## CLIで見る

```bash
python -m crypto_auto_trade.cli list-strategies
```

Best候補を選ぶ:

```bash
python -m crypto_auto_trade.cli best-strategy --iterations 300 --trailing-stop-pct 0.05
```

特定戦略をバックテスト:

```bash
python -m crypto_auto_trade.cli backtest --strategy ema_cross_f5_s34 --trailing-stop-pct 0.05
```

## 画面で見る

```bash
python -m crypto_auto_trade.web
```

ブラウザで開く:

```text
http://127.0.0.1:8000
```

画面上部の `Strategy` セレクトボックスに、5つの基本戦略と100種類以上のバリエーションが出ます。

## 必須ルール

全戦略共通で、**一度BUYしてポジションを持ったら必ずトレーリングストップを持つ**ようにしています。

実装場所:

```text
crypto_auto_trade/backtest.py
```

BUY時に:

```text
mandatory trailing stop armed
```

Stop発動時に:

```text
mandatory trailing stop hit
```

という理由がtrade logに入ります。
