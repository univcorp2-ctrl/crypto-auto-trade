# 100+ Strategy Variants Explained

![100+ Strategy Variants Map](assets/strategy-variants-map.svg)

## これは何か

このリポジトリの **100+ Strategy Variants** は、

> 5つの基本戦略ファミリーを、パラメータ違いで100種類以上に展開した検証候補

です。

100個の完全に別々のコードを手書きしているわけではありません。

理由はシンプルです。

- 完全手書き100個は壊れやすい
- 何が違うか分かりにくい
- 比較条件が揃わない
- メンテナンス不能になりやすい

そのため、構造はこうしています。

```text
基本戦略ファミリー = ロジックの考え方
バリエーション = その考え方の設定値違い
```

## Family と Variant の違い

![Family vs Variant](assets/strategy-family-vs-variant.svg)

### Family

Familyは「どういう考え方で勝とうとしているか」です。

例:

- EMAで順張りする
- RSIで逆張りする
- 高値ブレイクで入る
- ボラティリティ拡大に乗る
- 相場状態を判定して守りながら入る

### Variant

Variantは「その考え方の細かい設定違い」です。

例:

- EMAを 5 / 34 にする
- EMAを 20 / 200 にする
- RSI entryを20にする
- RSI entryを30にする
- Donchian lookbackを20にする
- Donchian lookbackを100にする

同じファミリーでも、設定値が変わると反応速度・勝ちやすい相場・リスクが変わります。

## バリエーション数

| Family | Count | 変えているもの |
|---|---:|---|
| `regime_guard` | 18 | slow EMA / breakout期間 / ATR閾値 |
| `ema_cross` | 24 | fast EMA / slow EMA |
| `donchian_trend` | 24 | lookback / position size |
| `rsi_reversion` | 24 | entry RSI / exit RSI / position size |
| `bollinger_breakout` | 24 | window / band multiplier / position size |

合計100種類以上です。

## 命名規則

![Naming Guide](assets/strategy-variant-naming-guide.svg)

### EMA Cross

```text
ema_cross_f5_s34
```

| 部分 | 意味 |
|---|---|
| `ema_cross` | EMA Cross系 |
| `f5` | fast EMA = 5 |
| `s34` | slow EMA = 34 |

これは「速い反応のEMA順張り」です。

### Donchian Trend

```text
donchian_l55_p100
```

| 部分 | 意味 |
|---|---|
| `donchian` | Donchian breakout系 |
| `l55` | lookback = 55 |
| `p100` | position = 100% |

これは「過去55本の高値ブレイクで大きく入る戦略」です。

### RSI Reversion

```text
rsi_rev_e30_x50_p50
```

| 部分 | 意味 |
|---|---|
| `rsi_rev` | RSI逆張り系 |
| `e30` | entry RSI = 30 |
| `x50` | exit RSI = 50 |
| `p50` | position = 50% |

これは「RSI 30以下で半分入り、RSI 50で逃げる戦略」です。

### Bollinger Breakout

```text
bollinger_w20_m2p0_p75
```

| 部分 | 意味 |
|---|---|
| `bollinger` | Bollinger breakout系 |
| `w20` | window = 20 |
| `m2p0` | band multiplier = 2.0 |
| `p75` | position = 75% |

これは「20本・2σの上抜けで75%入る戦略」です。

## どれが一番勝てそうか

![Selection Workflow](assets/strategy-selection-workflow.svg)

このリポジトリでは、Best候補を雰囲気ではなく検証で選びます。

評価に使うもの:

- average return
- max drawdown
- Sharpe-like score
- healthy-rate
- trailing stop count

CLI:

```bash
python -m crypto_auto_trade.cli best-strategy --iterations 300 --trailing-stop-pct 0.05
```

UI:

```bash
python -m crypto_auto_trade.web
```

画面で `Pick Best` を押します。

## どの戦略にも共通する出口

このリポジトリでは、入口のロジックは100種類以上ありますが、出口の防御ルールは共通です。

```text
ポジションを取る
  ↓
最高値を記録する
  ↓
最高値から trailing_stop_pct 下にstopを置く
  ↓
価格がstopに触れたら強制EXIT
```

つまり、どの戦略でも **BUY後は必ずトレーリングストップ** です。

実装:

```text
crypto_auto_trade/backtest.py
```

ログ:

```text
mandatory trailing stop armed
mandatory trailing stop hit
```

## 重要

Best候補は「現在のデータと条件で一番良さそうなもの」です。

これは利益保証ではありません。必ず以下の順に進めます。

1. Backtest
2. Forward Test
3. Realtime Validate
4. Paper Trading
5. Small Live Trading
