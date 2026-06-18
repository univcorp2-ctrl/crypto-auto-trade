from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategyVariantSpec:
    name: str
    family: str
    label: str
    category: str
    thesis: str
    best_for: str
    risk: str
    params: dict[str, Any]


CORE_FAMILIES = {
    "regime_guard": "相場を trend/range/shock に分けて、防御しながら入る初期推奨ロジック。",
    "ema_cross": "短期EMAと長期EMAの関係でトレンドを追うシンプルな順張り。",
    "donchian_trend": "過去高値・安値チャネルのブレイクで勢いに乗るロジック。",
    "rsi_reversion": "売られすぎを拾い、回復で逃げる平均回帰ロジック。",
    "bollinger_breakout": "ボラティリティ拡大とトレンド方向の上抜けを狙うロジック。",
}


def build_variant_specs() -> dict[str, StrategyVariantSpec]:
    specs: dict[str, StrategyVariantSpec] = {}

    # 18 Regime Guard variants
    for slow in [60, 80, 100]:
        for breakout in [35, 55, 75]:
            for atr_ratio in [0.06, 0.08]:
                name = f"regime_guard_s{slow}_b{breakout}_atr{int(atr_ratio * 100)}"
                specs[name] = StrategyVariantSpec(
                    name=name,
                    family="regime_guard",
                    label=f"Regime Guard slow={slow} breakout={breakout}",
                    category="balanced_defensive",
                    thesis="相場判定を優先し、危険な急変時は取引しない。",
                    best_for="BTC/ETHなど大型銘柄の混合相場",
                    risk="保守的すぎて初動を逃すことがある",
                    params={"slow_ema": slow, "breakout_lookback": breakout, "max_atr_ratio": atr_ratio},
                )

    # 24 EMA variants
    for fast in [5, 8, 12, 20]:
        for slow in [34, 48, 80, 120, 160, 200]:
            if fast >= slow:
                continue
            name = f"ema_cross_f{fast}_s{slow}"
            specs[name] = StrategyVariantSpec(
                name=name,
                family="ema_cross",
                label=f"EMA Cross {fast}/{slow}",
                category="trend_follow",
                thesis="短期平均が長期平均を上回る局面だけ乗る。",
                best_for="明確な上昇トレンド",
                risk="レンジでは往復ビンタになりやすい",
                params={"fast_ema": fast, "slow_ema": slow},
            )

    # 24 Donchian variants
    for lookback in [20, 35, 55, 75, 100, 150]:
        for target in [0.35, 0.5, 0.75, 1.0]:
            name = f"donchian_l{lookback}_p{int(target * 100)}"
            specs[name] = StrategyVariantSpec(
                name=name,
                family="donchian_trend",
                label=f"Donchian {lookback} / position {target:.0%}",
                category="breakout",
                thesis="過去高値ブレイクで勢いを確認してから入る。",
                best_for="大きな材料・資金流入で高値更新が続く相場",
                risk="フェイクブレイクに弱い",
                params={"lookback": lookback, "target_position": target},
            )

    # 24 RSI variants
    for entry in [20, 25, 30, 35]:
        for exit_rsi in [45, 50, 55]:
            for position in [0.25, 0.5]:
                name = f"rsi_rev_e{entry}_x{exit_rsi}_p{int(position * 100)}"
                specs[name] = StrategyVariantSpec(
                    name=name,
                    family="rsi_reversion",
                    label=f"RSI Reversion entry={entry} exit={exit_rsi}",
                    category="mean_reversion",
                    thesis="売られすぎだけ小さく拾い、回復したら逃げる。",
                    best_for="レンジ相場・大型銘柄の押し目",
                    risk="強い下落トレンドでは危険",
                    params={"entry_rsi": float(entry), "exit_rsi": float(exit_rsi), "target_position": position},
                )

    # 24 Bollinger variants
    for window in [14, 20, 30, 40]:
        for multiple in [1.5, 2.0, 2.5]:
            for position in [0.5, 0.75]:
                mult_code = str(multiple).replace(".", "p")
                name = f"bollinger_w{window}_m{mult_code}_p{int(position * 100)}"
                specs[name] = StrategyVariantSpec(
                    name=name,
                    family="bollinger_breakout",
                    label=f"Bollinger Breakout w={window} m={multiple}",
                    category="volatility_expansion",
                    thesis="上方向のボラティリティ拡大にだけ乗る。",
                    best_for="価格発見・ボラ拡大局面",
                    risk="上ヒゲ反落に弱い",
                    params={"window": window, "multiple": multiple, "target_position": position},
                )

    return specs


VARIANT_SPECS = build_variant_specs()


def variant_count() -> int:
    return len(VARIANT_SPECS)


def variant_descriptions() -> list[dict[str, str]]:
    return [
        {
            "name": spec.name,
            "label": spec.label,
            "family": spec.family,
            "style": spec.category,
            "best_for": spec.best_for,
            "risk": spec.risk,
        }
        for spec in VARIANT_SPECS.values()
    ]
