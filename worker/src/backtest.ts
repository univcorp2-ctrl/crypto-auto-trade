import { Candle, Signal, maxDrawdown, sharpeLike } from "./indicators";
import { generateSignals } from "./strategies";

const r6 = (v: number): number => Math.round(v * 1e6) / 1e6;

export interface Trade {
  timestamp: string;
  side: string;
  price: number;
  quantity: number;
  fee: number;
  cash_after: number;
  equity_after: number;
  reason: string;
  trailing_stop_price: number | null;
}

export interface BacktestConfig {
  initial_cash: number;
  fee_rate: number;
  slippage_bps: number;
  trailing_stop_pct: number;
}

export function defaultConfig(trailingStopPct = 0.05): BacktestConfig {
  if (!(trailingStopPct >= 0.001 && trailingStopPct <= 0.5)) throw new Error("trailing_stop_pct must be between 0.001 and 0.5");
  return { initial_cash: 10000, fee_rate: 0.001, slippage_bps: 5, trailing_stop_pct: trailingStopPct };
}

export interface BacktestResult {
  strategy: string;
  initial_cash: number;
  final_equity: number;
  total_return: number;
  max_drawdown: number;
  sharpe_like: number;
  win_rate: number;
  trailing_stop_pct: number;
  trade_count: number;
  trailing_stop_count: number;
  equity_curve: { timestamp: string; equity: number }[];
  trades: Trade[];
  latest_signal: Signal | null;
}

export function runBacktest(strategy: string, candles: Candle[], cfg: BacktestConfig): BacktestResult {
  if (candles.length < 90) throw new Error("at least 90 candles are recommended");
  const signals = generateSignals(strategy, candles);
  let cash = cfg.initial_cash;
  let units = 0;
  let avgEntry = 0;
  let peakPrice: number | null = null;
  let roundTrips = 0;
  let wins = 0;
  const trades: Trade[] = [];
  const equityCurve: [string, number][] = [];
  const slip = cfg.slippage_bps / 10000;

  for (let idx = 0; idx < candles.length; idx++) {
    const candle = candles[idx];
    const signal = signals[idx];
    const price = candle.close;

    if (units > 0) {
      peakPrice = peakPrice === null ? candle.high : Math.max(peakPrice, candle.high);
      const trailingStopPrice = peakPrice * (1 - cfg.trailing_stop_pct);
      if (candle.low <= trailingStopPrice) {
        const execution = trailingStopPrice * (1 - slip);
        const qty = units;
        const notional = qty * execution;
        const fee = notional * cfg.fee_rate;
        cash += notional - fee;
        const pnl = (execution - avgEntry) * qty - fee;
        roundTrips += 1;
        wins += pnl > 0 ? 1 : 0;
        units = 0;
        avgEntry = 0;
        peakPrice = null;
        trades.push({ timestamp: candle.timestamp, side: "SELL", price: execution, quantity: qty, fee, cash_after: cash, equity_after: cash, reason: `mandatory trailing stop hit (${(cfg.trailing_stop_pct * 100).toFixed(2)}%)`, trailing_stop_price: trailingStopPrice });
        equityCurve.push([candle.timestamp, cash]);
        continue;
      }
    }

    const equity = cash + units * price;
    const targetUnits = (equity * signal.target_position) / price;
    const delta = targetUnits - units;
    if (Math.abs(delta) > 1e-10) {
      let execution: number;
      let qty: number;
      let fee: number;
      let side: string;
      let reason: string;
      let trailingStopPrice: number | null;
      if (delta > 0) {
        execution = price * (1 + slip);
        qty = Math.min(delta, cash / (execution * (1 + cfg.fee_rate)));
        const notional = qty * execution;
        fee = notional * cfg.fee_rate;
        const previousUnits = units;
        cash -= notional + fee;
        units += qty;
        avgEntry = units ? (avgEntry * previousUnits + execution * qty) / units : 0;
        peakPrice = candle.high;
        trailingStopPrice = peakPrice * (1 - cfg.trailing_stop_pct);
        side = "BUY";
        reason = signal.reason + "; mandatory trailing stop armed";
      } else {
        execution = price * (1 - slip);
        qty = Math.min(Math.abs(delta), units);
        const notional = qty * execution;
        fee = notional * cfg.fee_rate;
        cash += notional - fee;
        units -= qty;
        trailingStopPrice = peakPrice ? peakPrice * (1 - cfg.trailing_stop_pct) : null;
        side = "SELL";
        reason = signal.reason;
        if (units <= 1e-10) {
          const pnl = (execution - avgEntry) * qty - fee;
          roundTrips += 1;
          wins += pnl > 0 ? 1 : 0;
          units = 0;
          avgEntry = 0;
          peakPrice = null;
        }
      }
      trades.push({ timestamp: candle.timestamp, side, price: execution, quantity: qty, fee, cash_after: cash, equity_after: cash + units * price, reason, trailing_stop_price: trailingStopPrice });
    }
    equityCurve.push([candle.timestamp, cash + units * price]);
  }

  const final = equityCurve[equityCurve.length - 1][1];
  const trailingStopCount = trades.filter((t) => t.reason.toLowerCase().includes("trailing stop")).length;
  return {
    strategy,
    initial_cash: r6(cfg.initial_cash),
    final_equity: r6(final),
    total_return: r6(final / cfg.initial_cash - 1),
    max_drawdown: r6(maxDrawdown(equityCurve.map(([, e]) => e))),
    sharpe_like: r6(sharpeLike(equityCurve)),
    win_rate: r6(roundTrips ? wins / roundTrips : 0),
    trailing_stop_pct: cfg.trailing_stop_pct,
    trade_count: trades.length,
    trailing_stop_count: trailingStopCount,
    equity_curve: equityCurve.map(([t, e]) => ({ timestamp: t, equity: r6(e) })),
    trades,
    latest_signal: signals.length ? signals[signals.length - 1] : null,
  };
}

export function forwardTest(strategy: string, candles: Candle[], cfg: BacktestConfig, splitRatio = 0.7): Record<string, unknown> {
  const split = Math.trunc(candles.length * splitRatio);
  const train = runBacktest(strategy, candles.slice(0, split), cfg);
  const forward = runBacktest(strategy, candles.slice(Math.max(0, split - 90)), cfg);
  let verdict = forward.total_return > 0 && forward.max_drawdown < 0.25 ? "healthy" : "watch";
  if (train.total_return > 0 && forward.total_return < 0) verdict = "overfit_or_regime_changed";
  if (forward.max_drawdown >= 0.35) verdict = "drawdown_too_high";
  return { strategy, split_index: split, train, forward, verdict };
}
