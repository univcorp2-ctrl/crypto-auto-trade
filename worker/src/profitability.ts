import { Candle } from "./indicators";
import { defaultConfig, forwardTest } from "./backtest";
import { runValidationMatrix, compareAllStrategies, SummaryRow } from "./validation";

export const VERDICT_LABELS: Record<string, string> = {
  win_likely: "勝てる可能性が高い",
  marginal: "条件付き・要監視",
  lose_likely: "現状の設定では勝ちにくい",
};

const r = (v: number, n: number): number => {
  const f = 10 ** n;
  return Math.round(v * f) / f;
};

export function verifyProfitability(candles: Candle[], trailingStopPct = 0.05, iterations = 300): Record<string, unknown> {
  const matrix = runValidationMatrix(candles, iterations, trailingStopPct) as { summary: SummaryRow[] };
  const summary = matrix.summary;
  if (!summary.length) throw new Error("validation produced no summary rows");
  const best = summary[0];
  const bestName = best.strategy;

  const backtestRows = compareAllStrategies(candles, trailingStopPct);
  const profitable = backtestRows.filter((row) => (row.total_return as number) > 0);
  const profitableRate = profitable.length / backtestRows.length;

  const forward = forwardTest(bestName, candles, defaultConfig(trailingStopPct)) as {
    forward: { total_return: number }; train: { total_return: number }; verdict: string;
  };
  const forwardReturn = forward.forward.total_return;
  const trainReturn = forward.train.total_return;

  const checks: Record<string, boolean> = {
    best_avg_return_positive: best.avg_return > 0,
    positive_rate_majority: best.positive_rate >= 0.5,
    healthy_rate_majority: best.healthy_rate >= 0.5,
    forward_return_positive: forwardReturn > 0,
    drawdown_acceptable: best.avg_drawdown < 0.25,
    library_mostly_profitable: profitableRate >= 0.5,
  };
  const winScore = Object.values(checks).filter(Boolean).length;
  const totalChecks = Object.keys(checks).length;

  let verdict: string;
  if (winScore >= 5 && checks.forward_return_positive) verdict = "win_likely";
  else if (winScore >= 3) verdict = "marginal";
  else verdict = "lose_likely";

  return {
    verdict,
    verdict_label: VERDICT_LABELS[verdict],
    win_score: winScore,
    max_score: totalChecks,
    confidence: r(winScore / totalChecks, 4),
    best_strategy: bestName,
    trailing_stop_pct: trailingStopPct,
    iterations,
    checks,
    metrics: {
      best_avg_return: r(best.avg_return, 6),
      best_positive_rate: r(best.positive_rate, 4),
      best_healthy_rate: r(best.healthy_rate, 4),
      best_avg_drawdown: r(best.avg_drawdown, 6),
      library_profitable_rate: r(profitableRate, 4),
      library_profitable_count: profitable.length,
      library_total: backtestRows.length,
      forward_train_return: r(trainReturn, 6),
      forward_return: r(forwardReturn, 6),
      forward_verdict: forward.verdict,
    },
    note: "Sample/historical judgement only. A 'win_likely' verdict means the strategy library was profitable and stable on this data with the current trailing stop; it is not a guarantee of future profit.",
  };
}
