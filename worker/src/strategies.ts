import { Candle, Signal, ema, atr, rsi, rollingZscore, bollingerBands, rangeEfficiency } from "./indicators";

export interface VariantSpec {
  name: string;
  family: string;
  label: string;
  category: string;
  best_for: string;
  risk: string;
  params: Record<string, number>;
}

// ----------------------------------------------------- variant spec builder
export function buildVariantSpecs(): Record<string, VariantSpec> {
  const specs: Record<string, VariantSpec> = {};

  for (const slow of [60, 80, 100])
    for (const breakout of [35, 55, 75])
      for (const atrRatio of [0.06, 0.08]) {
        const name = `regime_guard_s${slow}_b${breakout}_atr${Math.trunc(atrRatio * 100)}`;
        specs[name] = { name, family: "regime_guard", label: `Regime Guard slow=${slow} breakout=${breakout}`, category: "balanced_defensive", best_for: "BTC/ETHなど大型銘柄の混合相場", risk: "保守的すぎて初動を逃すことがある", params: { slow_ema: slow, breakout_lookback: breakout, max_atr_ratio: atrRatio } };
      }

  for (const fast of [5, 8, 12, 20])
    for (const slow of [34, 48, 80, 120, 160, 200]) {
      if (fast >= slow) continue;
      const name = `ema_cross_f${fast}_s${slow}`;
      specs[name] = { name, family: "ema_cross", label: `EMA Cross ${fast}/${slow}`, category: "trend_follow", best_for: "明確な上昇トレンド", risk: "レンジでは往復ビンタになりやすい", params: { fast_ema: fast, slow_ema: slow } };
    }

  for (const lookback of [20, 35, 55, 75, 100, 150])
    for (const target of [0.35, 0.5, 0.75, 1.0]) {
      const name = `donchian_l${lookback}_p${Math.trunc(target * 100)}`;
      specs[name] = { name, family: "donchian_trend", label: `Donchian ${lookback} / position ${Math.round(target * 100)}%`, category: "breakout", best_for: "大きな材料・資金流入で高値更新が続く相場", risk: "フェイクブレイクに弱い", params: { lookback, target_position: target } };
    }

  for (const entry of [20, 25, 30, 35])
    for (const exitRsi of [45, 50, 55])
      for (const position of [0.25, 0.5]) {
        const name = `rsi_rev_e${entry}_x${exitRsi}_p${Math.trunc(position * 100)}`;
        specs[name] = { name, family: "rsi_reversion", label: `RSI Reversion entry=${entry} exit=${exitRsi}`, category: "mean_reversion", best_for: "レンジ相場・大型銘柄の押し目", risk: "強い下落トレンドでは危険", params: { entry_rsi: entry, exit_rsi: exitRsi, target_position: position } };
      }

  for (const window of [14, 20, 30, 40])
    for (const multiple of [1.5, 2.0, 2.5])
      for (const position of [0.5, 0.75]) {
        const multCode = String(multiple).replace(".", "p");
        const name = `bollinger_w${window}_m${multCode}_p${Math.trunc(position * 100)}`;
        specs[name] = { name, family: "bollinger_breakout", label: `Bollinger Breakout w=${window} m=${multiple}`, category: "volatility_expansion", best_for: "価格発見・ボラ拡大局面", risk: "上ヒゲ反落に弱い", params: { window, multiple, target_position: position } };
      }

  return specs;
}

export const VARIANT_SPECS = buildVariantSpecs();

const CORE_NAMES = ["regime_guard", "ema_cross", "donchian_trend", "rsi_reversion", "bollinger_breakout"];

export function strategyNames(): string[] {
  return [...CORE_NAMES, ...Object.keys(VARIANT_SPECS)].sort();
}

const sig = (c: Candle, previous: number, target: number, regime: string, reason: string, risk = 0): Signal => ({
  timestamp: c.timestamp,
  action: target > previous ? "BUY" : target < previous ? "SELL" : "HOLD",
  target_position: Math.round(target * 1e6) / 1e6,
  regime,
  reason,
  risk_score: Math.round(risk * 100) / 100,
});

type Params = Record<string, number>;

// ----------------------------------------------------- strategy signal logic
function regimeGuard(candles: Candle[], p: Params): Signal[] {
  const fastEma = p.fast_ema ?? 20, slowEma = p.slow_ema ?? 80, atrWindow = p.atr_window ?? 14;
  const breakoutLookback = p.breakout_lookback ?? 55, zWindow = p.z_window ?? 40;
  const maxAtrRatio = p.max_atr_ratio ?? 0.08, efficiencyThreshold = p.efficiency_threshold ?? 0.25;
  const meanEntryZ = p.mean_entry_z ?? -1.8, meanExitZ = p.mean_exit_z ?? 0.4;
  const maxPosition = p.max_position ?? 1.0, sidewaysPosition = p.sideways_position ?? 0.35;
  const closes = candles.map((c) => c.close), highs = candles.map((c) => c.high), lows = candles.map((c) => c.low);
  const fast = ema(closes, fastEma), slow = ema(closes, slowEma), atrs = atr(highs, lows, closes, atrWindow), zs = rollingZscore(closes, zWindow);
  let target = 0;
  const out: Signal[] = [];
  const minHistory = Math.max(slowEma + 10, breakoutLookback + 1, zWindow + 1, atrWindow + 1);
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i];
    const previous = target;
    if (i < minHistory || fast[i] === null || slow[i] === null || atrs[i] === null || zs[i] === null) {
      out.push(sig(c, previous, 0, "warmup", "not enough history"));
      continue;
    }
    const atrRatio = (atrs[i] ?? 0) / c.close;
    const risk = Math.min(100, (atrRatio / maxAtrRatio) * 100);
    const efficiency = rangeEfficiency(closes, breakoutLookback, i) ?? 0;
    const prevHigh = Math.max(...highs.slice(i - breakoutLookback, i));
    const prevLow = Math.min(...lows.slice(i - breakoutLookback, i));
    const shock = atrRatio > maxAtrRatio;
    const trendUp = c.close > (slow[i] ?? 0) && (fast[i] ?? 0) > (slow[i] ?? 0) && efficiency >= efficiencyThreshold;
    const trendDown = c.close < (slow[i] ?? 0) && (fast[i] ?? 0) < (slow[i] ?? 0);
    if (shock || trendDown) { target = 0; out.push(sig(c, previous, target, "risk_off", "shock/downtrend filter", risk)); }
    else if (trendUp && c.close > prevHigh) { target = maxPosition; out.push(sig(c, previous, target, "trend_up", "Donchian breakout with EMA trend", risk)); }
    else if (previous > 0 && (c.close < prevLow || c.close < (slow[i] ?? 0))) { target = 0; out.push(sig(c, previous, target, "exit", "price broke exit reference", risk)); }
    else if (target === 0 && (zs[i] ?? 0) <= meanEntryZ) { target = sidewaysPosition; out.push(sig(c, previous, target, "sideways", "small mean reversion", risk)); }
    else if (target > 0 && (zs[i] ?? 0) >= meanExitZ) { target = 0; out.push(sig(c, previous, target, "sideways_exit", "mean reversion recovered", risk)); }
    else out.push(sig(c, previous, target, "wait", "no confirmed edge", risk));
  }
  return out;
}

function emaCross(candles: Candle[], p: Params): Signal[] {
  const fastEma = p.fast_ema ?? 12, slowEma = p.slow_ema ?? 48, targetPosition = p.target_position ?? 1.0;
  const closes = candles.map((c) => c.close);
  const fast = ema(closes, fastEma), slow = ema(closes, slowEma);
  let target = 0;
  const out: Signal[] = [];
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i], previous = target;
    if (i < slowEma || fast[i] === null || slow[i] === null) { out.push(sig(c, previous, 0, "warmup", "not enough history")); continue; }
    target = (fast[i] ?? 0) > (slow[i] ?? 0) ? targetPosition : 0;
    out.push(sig(c, previous, target, "trend", "fast EMA above/below slow EMA"));
  }
  return out;
}

function donchianTrend(candles: Candle[], p: Params): Signal[] {
  const lookback = p.lookback ?? 55, targetPosition = p.target_position ?? 1.0;
  const highs = candles.map((c) => c.high), lows = candles.map((c) => c.low);
  const highBand = highs.map((_, i) => (i + 1 < lookback ? null : Math.max(...highs.slice(i + 1 - lookback, i + 1))));
  const lowBand = lows.map((_, i) => (i + 1 < lookback ? null : Math.min(...lows.slice(i + 1 - lookback, i + 1))));
  let target = 0;
  const out: Signal[] = [];
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i], previous = target;
    if (i <= lookback || highBand[i - 1] === null || lowBand[i - 1] === null) { out.push(sig(c, previous, 0, "warmup", "not enough history")); continue; }
    let reason = "inside channel";
    if (c.close > (highBand[i - 1] ?? 0)) { target = targetPosition; reason = "close broke previous channel high"; }
    else if (c.close < (lowBand[i - 1] ?? 0)) { target = 0; reason = "close broke previous channel low"; }
    out.push(sig(c, previous, target, "channel", reason));
  }
  return out;
}

function rsiReversion(candles: Candle[], p: Params): Signal[] {
  const rsiWindow = p.rsi_window ?? 14, atrWindow = p.atr_window ?? 14;
  const entryRsi = p.entry_rsi ?? 30, exitRsi = p.exit_rsi ?? 52, targetPosition = p.target_position ?? 0.5, maxAtrRatio = p.max_atr_ratio ?? 0.08;
  const closes = candles.map((c) => c.close), highs = candles.map((c) => c.high), lows = candles.map((c) => c.low);
  const rsis = rsi(closes, rsiWindow), atrs = atr(highs, lows, closes, atrWindow);
  let target = 0;
  const out: Signal[] = [];
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i], previous = target;
    if (i < Math.max(rsiWindow, atrWindow) || rsis[i] === null || atrs[i] === null) { out.push(sig(c, previous, 0, "warmup", "not enough history")); continue; }
    const risk = Math.min(100, ((atrs[i] ?? 0) / c.close / maxAtrRatio) * 100);
    let reason = "RSI wait";
    if (risk > 100) { target = 0; reason = "volatility shock"; }
    else if (target === 0 && (rsis[i] ?? 0) <= entryRsi) { target = targetPosition; reason = "RSI oversold entry"; }
    else if (target > 0 && (rsis[i] ?? 0) >= exitRsi) { target = 0; reason = "RSI recovery exit"; }
    out.push(sig(c, previous, target, "rsi", reason, risk));
  }
  return out;
}

function bollingerBreakout(candles: Candle[], p: Params): Signal[] {
  const window = p.window ?? 20, multiple = p.multiple ?? 2.0, trendEma = p.trend_ema ?? 80, targetPosition = p.target_position ?? 0.75;
  const closes = candles.map((c) => c.close);
  const [middle, upper] = bollingerBands(closes, window, multiple);
  const trend = ema(closes, trendEma);
  let target = 0;
  const out: Signal[] = [];
  const minHistory = Math.max(window, trendEma);
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i], previous = target;
    if (i < minHistory || middle[i] === null || upper[i] === null || trend[i] === null) { out.push(sig(c, previous, 0, "warmup", "not enough history")); continue; }
    let reason = "breakout wait";
    if (target === 0 && c.close > (upper[i] ?? 0) && c.close > (trend[i] ?? 0)) { target = targetPosition; reason = "Bollinger breakout"; }
    else if (target > 0 && c.close < (middle[i] ?? 0)) { target = 0; reason = "below middle band exit"; }
    out.push(sig(c, previous, target, "bollinger", reason));
  }
  return out;
}

const FAMILY: Record<string, (candles: Candle[], p: Params) => Signal[]> = {
  regime_guard: regimeGuard,
  ema_cross: emaCross,
  donchian_trend: donchianTrend,
  rsi_reversion: rsiReversion,
  bollinger_breakout: bollingerBreakout,
};

export function generateSignals(name: string, candles: Candle[]): Signal[] {
  if (CORE_NAMES.includes(name)) return FAMILY[name](candles, {});
  const spec = VARIANT_SPECS[name];
  if (!spec) throw new Error(`unknown strategy: ${name}`);
  return FAMILY[spec.family](candles, spec.params);
}

export function strategyDescriptions(includeVariants = true): Record<string, string>[] {
  const core = [
    { name: "regime_guard", label: "Regime Guard", family: "regime_guard", style: "trend + range + shock filter", best_for: "mixed markets", risk: "may skip pumps" },
    { name: "ema_cross", label: "EMA Cross", family: "ema_cross", style: "trend follow", best_for: "clean trends", risk: "range whipsaw" },
    { name: "donchian_trend", label: "Donchian Trend", family: "donchian_trend", style: "breakout", best_for: "strong breakouts", risk: "fake breakout" },
    { name: "rsi_reversion", label: "RSI Reversion", family: "rsi_reversion", style: "mean reversion", best_for: "ranges", risk: "downtrend" },
    { name: "bollinger_breakout", label: "Bollinger Breakout", family: "bollinger_breakout", style: "volatility expansion", best_for: "expansion", risk: "fake breakout" },
  ];
  if (includeVariants)
    for (const s of Object.values(VARIANT_SPECS)) core.push({ name: s.name, label: s.label, family: s.family, style: s.category, best_for: s.best_for, risk: s.risk });
  return core;
}
