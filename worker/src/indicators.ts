// Faithful TypeScript port of the Python trading engine
// (crypto_auto_trade: indicators, strategy_variants, strategies, backtest,
// validation, profitability) so the dashboard runs natively on Cloudflare
// Workers. Numeric behavior mirrors the Python reference.

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Signal {
  timestamp: string;
  action: string;
  target_position: number;
  regime: string;
  reason: string;
  risk_score: number;
}

const r6 = (v: number): number => Math.round(v * 1e6) / 1e6;

// ---------------------------------------------------------------- sample data
export function generateSampleCandles(count = 360): Candle[] {
  const candles: Candle[] = [];
  let price = 100.0;
  for (let i = 0; i < count; i++) {
    const drift = i < count * 0.38 ? 0.0025 : i < count * 0.62 ? -0.0018 : 0.001;
    const cycle = Math.sin(i / 9) * 0.008 + Math.sin(i / 31) * 0.01;
    const shock = i === 160 || i === 161 ? -0.08 : i === 250 || i === 251 ? 0.05 : 0.0;
    const prev = price;
    price = Math.max(5.0, price * (1 + drift + cycle + shock));
    const high = Math.max(prev, price) * 1.006;
    const low = Math.min(prev, price) * 0.994;
    candles.push({ timestamp: `2026-01-01T${String(i).padStart(4, "0")}:00:00Z`, open: prev, high, low, close: price, volume: 1000 + i });
  }
  return candles;
}

// ---------------------------------------------------------------- indicators
export function sma(values: number[], window: number): (number | null)[] {
  const out: (number | null)[] = [];
  let total = 0;
  for (let i = 0; i < values.length; i++) {
    total += values[i];
    if (i >= window) total -= values[i - window];
    out.push(i + 1 >= window ? total / window : null);
  }
  return out;
}

export function ema(values: number[], window: number): (number | null)[] {
  if (values.length === 0) return [];
  const alpha = 2 / (window + 1);
  const out: (number | null)[] = [];
  let current = values[0];
  for (let i = 0; i < values.length; i++) {
    current = i === 0 ? values[i] : alpha * values[i] + (1 - alpha) * current;
    out.push(i + 1 >= window ? current : null);
  }
  return out;
}

export function rsi(values: number[], window = 14): (number | null)[] {
  if (values.length < 2) return values.map(() => null);
  const out: (number | null)[] = [null];
  const gains: number[] = [];
  const losses: number[] = [];
  for (let i = 1; i < values.length; i++) {
    const change = values[i] - values[i - 1];
    gains.push(Math.max(change, 0));
    losses.push(Math.abs(Math.min(change, 0)));
    if (i < window) {
      out.push(null);
      continue;
    }
    // Python slices gains[i-window:i] / losses[i-window:i]; gains is 0-indexed
    // from i=1, so gains[k] corresponds to change at values[k+1].
    let avgGain = 0;
    let avgLoss = 0;
    for (let k = i - window; k < i; k++) {
      avgGain += gains[k];
      avgLoss += losses[k];
    }
    avgGain /= window;
    avgLoss /= window;
    out.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
  }
  return out;
}

export function atr(highs: number[], lows: number[], closes: number[], window: number): (number | null)[] {
  const tr: number[] = [];
  for (let i = 0; i < highs.length; i++) {
    const low = lows[i];
    if (i === 0) tr.push(highs[i] - low);
    else {
      const prev = closes[i - 1];
      tr.push(Math.max(highs[i] - low, Math.abs(highs[i] - prev), Math.abs(low - prev)));
    }
  }
  return sma(tr, window);
}

export function rollingZscore(values: number[], window: number): (number | null)[] {
  const out: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i + 1 < window) {
      out.push(null);
      continue;
    }
    const seg = values.slice(i + 1 - window, i + 1);
    const mean = seg.reduce((a, b) => a + b, 0) / window;
    const variance = seg.reduce((a, b) => a + (b - mean) ** 2, 0) / window;
    const std = Math.sqrt(variance);
    out.push(std === 0 ? 0 : (values[i] - mean) / std);
  }
  return out;
}

export function bollingerBands(values: number[], window = 20, multiple = 2.0): [(number | null)[], (number | null)[], (number | null)[]] {
  const middle = sma(values, window);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i + 1 < window || middle[i] === null) {
      upper.push(null);
      lower.push(null);
      continue;
    }
    const seg = values.slice(i + 1 - window, i + 1);
    const mean = middle[i] ?? 0;
    const std = Math.sqrt(seg.reduce((a, b) => a + (b - mean) ** 2, 0) / window);
    upper.push(mean + multiple * std);
    lower.push(mean - multiple * std);
  }
  return [middle, upper, lower];
}

export function rangeEfficiency(values: number[], lookback: number, index: number): number | null {
  if (index < lookback) return null;
  const displacement = Math.abs(values[index] - values[index - lookback]);
  let path = 0;
  for (let i = index - lookback + 1; i <= index; i++) path += Math.abs(values[i] - values[i - 1]);
  return path === 0 ? 0 : displacement / path;
}

export function maxDrawdown(equity: number[]): number {
  let peak = -Infinity;
  let worst = 0;
  for (const value of equity) {
    peak = Math.max(peak, value);
    if (peak > 0) worst = Math.min(worst, value / peak - 1);
  }
  return Math.abs(worst);
}

export function sharpeLike(curve: [string, number][], periodsPerYear = 365 * 24): number {
  const returns: number[] = [];
  for (let i = 1; i < curve.length; i++) if (curve[i - 1][1] > 0) returns.push(curve[i][1] / curve[i - 1][1] - 1);
  if (returns.length < 2) return 0;
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const variance = returns.reduce((a, b) => a + (b - mean) ** 2, 0) / (returns.length - 1);
  const std = Math.sqrt(variance);
  return std === 0 ? 0 : (mean / std) * Math.sqrt(periodsPerYear);
}
