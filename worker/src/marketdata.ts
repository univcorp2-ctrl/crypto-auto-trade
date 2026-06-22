import { Candle } from "./indicators";

// Live OHLCV providers. Cloudflare Workers cannot use ccxt, and several large
// venues (Binance, Bybit) are geo-blocked from Cloudflare's edge, so we try a
// list of public REST endpoints in order and use the FIRST one that returns
// usable candles. Every provider normalizes to ascending Candle[] with ISO
// timestamps. A provider throws when it is unreachable or cannot serve the
// requested timeframe, and the caller falls through to the next one.

export interface LiveResult {
  candles: Candle[];
  provider: string;
}

type Provider = {
  name: string;
  fetch: (base: string, quote: string, timeframe: string, limit: number) => Promise<Candle[]>;
};

const iso = (ms: number): string => new Date(ms).toISOString();

async function getJson(url: string): Promise<unknown> {
  const res = await fetch(url, { headers: { accept: "application/json", "user-agent": "crypto-auto-trade/1.0" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// --- Binance (best when reachable; often 451 from Cloudflare) ---
const BINANCE_TF: Record<string, string> = {
  "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
  "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "12h": "12h", "1d": "1d",
};
const binance: Provider = {
  name: "binance",
  async fetch(base, quote, tf, limit) {
    const interval = BINANCE_TF[tf];
    if (!interval) throw new Error(`binance: unsupported timeframe ${tf}`);
    const sym = `${base}${quote}`.toUpperCase();
    const url = `https://api.binance.com/api/v3/klines?symbol=${sym}&interval=${interval}&limit=${Math.min(Math.max(limit, 90), 1000)}`;
    const rows = (await getJson(url)) as unknown[][];
    return rows.map((r) => ({
      timestamp: iso(Number(r[0])), open: Number(r[1]), high: Number(r[2]),
      low: Number(r[3]), close: Number(r[4]), volume: Number(r[5]),
    }));
  },
};

// --- Kraken (ascending, seconds, result keyed by canonical pair) ---
const KRAKEN_TF: Record<string, number> = { "1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440 };
const kraken: Provider = {
  name: "kraken",
  async fetch(base, quote, tf, limit) {
    const interval = KRAKEN_TF[tf];
    if (!interval) throw new Error(`kraken: unsupported timeframe ${tf}`);
    const kBase = base.toUpperCase() === "BTC" ? "XBT" : base.toUpperCase();
    const pair = `${kBase}${quote.toUpperCase()}`;
    const url = `https://api.kraken.com/0/public/OHLC?pair=${pair}&interval=${interval}`;
    const body = (await getJson(url)) as { error?: string[]; result?: Record<string, unknown> };
    if (body.error && body.error.length) throw new Error(`kraken: ${body.error.join(",")}`);
    const result = body.result ?? {};
    const key = Object.keys(result).find((k) => k !== "last");
    if (!key) throw new Error("kraken: no result");
    const rows = result[key] as unknown[][];
    return rows.slice(-limit).map((r) => ({
      timestamp: iso(Number(r[0]) * 1000), open: Number(r[1]), high: Number(r[2]),
      low: Number(r[3]), close: Number(r[4]), volume: Number(r[6]),
    }));
  },
};

// --- Coinbase Exchange (descending, seconds, [time,low,high,open,close,vol]) ---
const COINBASE_TF: Record<string, number> = { "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "6h": 21600, "1d": 86400 };
const coinbase: Provider = {
  name: "coinbase",
  async fetch(base, quote, tf, limit) {
    const granularity = COINBASE_TF[tf];
    if (!granularity) throw new Error(`coinbase: unsupported timeframe ${tf}`);
    const product = `${base.toUpperCase()}-${quote.toUpperCase()}`;
    const url = `https://api.exchange.coinbase.com/products/${product}/candles?granularity=${granularity}`;
    const rows = (await getJson(url)) as number[][];
    return rows
      .map((r) => ({
        timestamp: iso(Number(r[0]) * 1000), low: Number(r[1]), high: Number(r[2]),
        open: Number(r[3]), close: Number(r[4]), volume: Number(r[5]),
      }))
      .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      .slice(-limit);
  },
};

// --- OKX (descending, ms, [ts,o,h,l,c,vol,...]) ---
const OKX_TF: Record<string, string> = {
  "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
  "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H", "1d": "1D",
};
const okx: Provider = {
  name: "okx",
  async fetch(base, quote, tf, limit) {
    const bar = OKX_TF[tf];
    if (!bar) throw new Error(`okx: unsupported timeframe ${tf}`);
    const instId = `${base.toUpperCase()}-${quote.toUpperCase()}`;
    const url = `https://www.okx.com/api/v5/market/candles?instId=${instId}&bar=${bar}&limit=${Math.min(Math.max(limit, 90), 300)}`;
    const body = (await getJson(url)) as { code?: string; data?: unknown[][] };
    if (body.code && body.code !== "0") throw new Error(`okx: code ${body.code}`);
    const rows = body.data ?? [];
    return rows
      .map((r) => ({
        timestamp: iso(Number(r[0])), open: Number(r[1]), high: Number(r[2]),
        low: Number(r[3]), close: Number(r[4]), volume: Number(r[5]),
      }))
      .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      .slice(-limit);
  },
};

// --- CoinGecko OHLC (ascending, ms, [ts,o,h,l,c], NO volume; coarse) ---
const COINGECKO_IDS: Record<string, string> = {
  BTC: "bitcoin", ETH: "ethereum", SOL: "solana", XRP: "ripple", BNB: "binancecoin",
  ADA: "cardano", DOGE: "dogecoin", AVAX: "avalanche-2", LINK: "chainlink", MATIC: "matic-network",
  DOT: "polkadot", LTC: "litecoin", TRX: "tron", ATOM: "cosmos", UNI: "uniswap",
};
const coingecko: Provider = {
  name: "coingecko",
  async fetch(base, quote, tf, limit) {
    const id = COINGECKO_IDS[base.toUpperCase()];
    if (!id) throw new Error(`coingecko: unknown coin ${base}`);
    const vs = ["USDT", "USDC", "BUSD"].includes(quote.toUpperCase()) ? "usd" : quote.toLowerCase();
    // Granularity is auto from the day window: <=2d -> 30m, <=30d -> 4h, else daily.
    const days = limit >= 300 ? 90 : limit >= 120 ? 30 : 14;
    const url = `https://api.coingecko.com/api/v3/coins/${id}/ohlc?vs_currency=${vs}&days=${days}`;
    const rows = (await getJson(url)) as number[][];
    return rows.slice(-limit).map((r) => ({
      timestamp: iso(Number(r[0])), open: Number(r[1]), high: Number(r[2]),
      low: Number(r[3]), close: Number(r[4]), volume: 0,
    }));
  },
};

// Order matters: cheapest/most-accurate first, coarse last resort last.
export const PROVIDERS: Provider[] = [binance, kraken, coinbase, okx, coingecko];

function parseSymbol(symbol: string): { base: string; quote: string } {
  if (symbol.includes("/")) {
    const [base, quote] = symbol.split("/");
    return { base, quote: quote || "USDT" };
  }
  const up = symbol.toUpperCase();
  for (const q of ["USDT", "USDC", "USD", "EUR", "BTC"]) {
    if (up.endsWith(q) && up.length > q.length) return { base: up.slice(0, -q.length), quote: q };
  }
  return { base: up, quote: "USDT" };
}

export interface ProbeEntry {
  provider: string;
  ok: boolean;
  candles?: number;
  last_close?: number;
  error?: string;
}

// Try each provider in order; return the first that yields candles.
export async function fetchLiveCandlesMulti(symbol: string, timeframe: string, limit: number): Promise<LiveResult> {
  const { base, quote } = parseSymbol(symbol);
  const errors: string[] = [];
  for (const p of PROVIDERS) {
    try {
      const candles = await p.fetch(base, quote, timeframe, limit);
      if (candles.length >= 30 && candles.every((c) => Number.isFinite(c.close) && c.close > 0)) {
        return { candles, provider: p.name };
      }
      errors.push(`${p.name}: too few/invalid candles`);
    } catch (err) {
      errors.push(`${p.name}: ${err instanceof Error ? err.message : String(err)}`);
    }
  }
  throw new Error(`all live providers failed -> ${errors.join(" | ")}`);
}

// Diagnostic: probe every provider and report which actually serve live data.
export async function probeProviders(symbol: string, timeframe: string, limit: number): Promise<ProbeEntry[]> {
  const { base, quote } = parseSymbol(symbol);
  return Promise.all(
    PROVIDERS.map(async (p): Promise<ProbeEntry> => {
      try {
        const candles = await p.fetch(base, quote, timeframe, limit);
        return { provider: p.name, ok: candles.length >= 30, candles: candles.length, last_close: candles.at(-1)?.close };
      } catch (err) {
        return { provider: p.name, ok: false, error: err instanceof Error ? err.message : String(err) };
      }
    }),
  );
}
