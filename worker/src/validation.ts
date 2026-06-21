import { Candle } from "./indicators";
import { strategyNames } from "./strategies";
import { BacktestConfig, defaultConfig, runBacktest, forwardTest } from "./backtest";

const r = (v: number, n: number): number => {
  const f = 10 ** n;
  return Math.round(v * f) / f;
};

export interface MatrixRow {
  strategy: string;
  window: number;
  start: number;
  total_return: number;
  max_drawdown: number;
  sharpe_like: number;
  trade_count: number;
  trailing_stop_count: number;
  verdict: string;
}

export interface SummaryRow {
  strategy: string;
  runs: number;
  positive_rate: number;
  healthy_rate: number;
  avg_return: number;
  avg_drawdown: number;
  avg_sharpe_like: number;
  total_trailing_stops: number;
  selection_score: number;
}

export function runValidationMatrix(candles: Candle[], iterations = 200, trailingStopPct = 0.05): Record<string, unknown> {
  if (candles.length < 120) throw new Error("validation needs at least 120 candles");
  const names = strategyNames();
  const rows: MatrixRow[] = [];
  const config = defaultConfig(trailingStopPct);
  for (let i = 0; i < iterations; i++) {
    const name = names[i % names.length];
    const window = Math.min(candles.length, 120 + ((i * 17) % Math.max(1, candles.length - 119)));
    const start = (i * 13) % Math.max(1, candles.length - window + 1);
    const result = runBacktest(name, candles.slice(start, start + window), config);
    let verdict = result.total_return > 0 && result.max_drawdown < 0.25 ? "healthy" : "watch";
    if (result.max_drawdown >= 0.35) verdict = "risk_high";
    rows.push({
      strategy: name,
      window,
      start,
      total_return: r(result.total_return, 6),
      max_drawdown: r(result.max_drawdown, 6),
      sharpe_like: r(result.sharpe_like, 6),
      trade_count: result.trade_count,
      trailing_stop_count: result.trailing_stop_count,
      verdict,
    });
  }
  const summary = summarize(rows);
  return { iterations, trailing_stop_pct: trailingStopPct, summary, best: summary[0] ?? null, rows };
}

export function summarize(rows: MatrixRow[]): SummaryRow[] {
  const out: SummaryRow[] = [];
  const names = [...new Set(rows.map((r) => r.strategy))].sort();
  for (const name of names) {
    const selected = rows.filter((r) => r.strategy === name);
    const positives = selected.filter((r) => r.total_return > 0).length;
    const healthy = selected.filter((r) => r.verdict === "healthy").length;
    const avgReturn = selected.reduce((a, b) => a + b.total_return, 0) / selected.length;
    const avgDrawdown = selected.reduce((a, b) => a + b.max_drawdown, 0) / selected.length;
    const avgSharpe = selected.reduce((a, b) => a + b.sharpe_like, 0) / selected.length;
    const score = avgReturn * 100 + avgSharpe - avgDrawdown * 50 + (healthy / selected.length) * 10;
    out.push({
      strategy: name,
      runs: selected.length,
      positive_rate: r(positives / selected.length, 4),
      healthy_rate: r(healthy / selected.length, 4),
      avg_return: r(avgReturn, 6),
      avg_drawdown: r(avgDrawdown, 6),
      avg_sharpe_like: r(avgSharpe, 6),
      total_trailing_stops: selected.reduce((a, b) => a + b.trailing_stop_count, 0),
      selection_score: r(score, 6),
    });
  }
  return out.sort((a, b) => b.selection_score - a.selection_score);
}

export function compareAllStrategies(candles: Candle[], trailingStopPct = 0.05): Record<string, unknown>[] {
  const config = defaultConfig(trailingStopPct);
  const rows = strategyNames().map((name) => runBacktest(name, candles, config) as unknown as Record<string, unknown>);
  return rows.sort((a, b) => {
    const ar = a.total_return as number, br = b.total_return as number;
    if (br !== ar) return br - ar;
    return (a.max_drawdown as number) - (b.max_drawdown as number);
  });
}

export function forwardAllStrategies(candles: Candle[], trailingStopPct = 0.05): Record<string, unknown>[] {
  const config = defaultConfig(trailingStopPct);
  return strategyNames().map((name) => forwardTest(name, candles, config));
}

export function selectBestStrategy(candles: Candle[], iterations = 300, trailingStopPct = 0.05): Record<string, unknown> {
  const matrix = runValidationMatrix(candles, iterations, trailingStopPct);
  return {
    method: "rolling-window validation across all registered strategy variants",
    note: "This is not a profit guarantee. It selects the strongest historical candidate under the current sample/data and trailing stop setting.",
    best: (matrix as { best: unknown }).best,
    strategy_count: strategyNames().length,
    iterations,
    trailing_stop_pct: trailingStopPct,
  };
}

export { BacktestConfig };
