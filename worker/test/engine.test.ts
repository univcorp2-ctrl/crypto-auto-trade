import { describe, it, expect } from "vitest";
import { generateSampleCandles } from "../src/indicators";
import { strategyNames } from "../src/strategies";
import { defaultConfig, runBacktest } from "../src/backtest";
import { verifyProfitability, VERDICT_LABELS } from "../src/profitability";
import { VENUES } from "../src/exchanges";

// Reference values produced by the Python engine on generateSampleCandles(360),
// trailing_stop_pct=0.05. The TS port must match to 6 decimals.
const REFERENCE: Record<string, { total_return: number; max_drawdown: number; trade_count: number; trailing_stop_count: number }> = {
  regime_guard: { total_return: 0.225408, max_drawdown: 0.032075, trade_count: 26, trailing_stop_count: 14 },
  ema_cross: { total_return: 1.108916, max_drawdown: 0.129076, trade_count: 16, trailing_stop_count: 15 },
  donchian_trend: { total_return: 1.123089, max_drawdown: 0.129076, trade_count: 16, trailing_stop_count: 15 },
  rsi_reversion: { total_return: -0.354201, max_drawdown: 0.354201, trade_count: 143, trailing_stop_count: 119 },
  bollinger_breakout: { total_return: 0.403723, max_drawdown: 0.019598, trade_count: 87, trailing_stop_count: 20 },
  ema_cross_f5_s34: { total_return: 1.654595, max_drawdown: 0.111019, trade_count: 14, trailing_stop_count: 12 },
};

describe("engine parity with Python", () => {
  const candles = generateSampleCandles(360);

  it("registers the same strategy and exchange counts", () => {
    expect(strategyNames().length).toBe(119);
    expect(VENUES.length).toBe(32);
  });

  for (const [name, ref] of Object.entries(REFERENCE)) {
    it(`backtest matches Python for ${name}`, () => {
      const r = runBacktest(name, candles, defaultConfig(0.05));
      expect(r.total_return).toBeCloseTo(ref.total_return, 6);
      expect(r.max_drawdown).toBeCloseTo(ref.max_drawdown, 6);
      expect(r.trade_count).toBe(ref.trade_count);
      expect(r.trailing_stop_count).toBe(ref.trailing_stop_count);
    });
  }

  it("verify-profitability returns a valid verdict", () => {
    const result = verifyProfitability(candles, 0.05, 120) as Record<string, unknown>;
    expect(Object.keys(VERDICT_LABELS)).toContain(result.verdict);
    expect(result.max_score).toBe(6);
  });
});
