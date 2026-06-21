import { Candle, generateSampleCandles } from "./indicators";
import { strategyNames, strategyDescriptions } from "./strategies";
import { defaultConfig, runBacktest, forwardTest } from "./backtest";
import { runValidationMatrix, compareAllStrategies, forwardAllStrategies, selectBestStrategy } from "./validation";
import { verifyProfitability } from "./profitability";
import { VENUES, apiReadyVenues } from "./exchanges";

interface Env {
  ASSETS: { fetch: (request: Request) => Promise<Response> };
}

const json = (data: unknown, status = 200): Response =>
  new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json; charset=utf-8" } });

const num = (params: URLSearchParams, key: string, fallback: number): number => {
  const v = params.get(key);
  if (v === null || v === "") return fallback;
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
};

// Workers have no ccxt; fetch live OHLCV from Binance public klines when possible.
async function fetchLiveCandles(symbol: string, timeframe: string, limit: number): Promise<Candle[]> {
  const pair = symbol.replace("/", "").toUpperCase();
  const url = `https://api.binance.com/api/v3/klines?symbol=${encodeURIComponent(pair)}&interval=${encodeURIComponent(timeframe)}&limit=${Math.min(Math.max(limit, 90), 1000)}`;
  const res = await fetch(url, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error(`binance klines HTTP ${res.status}`);
  const rows = (await res.json()) as unknown[][];
  return rows.map((r) => ({ timestamp: String(r[0]), open: Number(r[1]), high: Number(r[2]), low: Number(r[3]), close: Number(r[4]), volume: Number(r[5]) }));
}

async function chooseCandles(dataSource: string, live: boolean, symbol: string, timeframe: string, limit: number): Promise<{ candles: Candle[]; source: string }> {
  if (live || dataSource === "live") {
    try {
      return { candles: await fetchLiveCandles(symbol, timeframe, limit), source: "live" };
    } catch {
      return { candles: generateSampleCandles(360).slice(-limit), source: "sample_fallback" };
    }
  }
  return { candles: generateSampleCandles(360).slice(-limit), source: "sample" };
}

async function handleApi(url: URL): Promise<Response> {
  const path = url.pathname;
  const q = url.searchParams;
  const trailing = num(q, "trailing_stop_pct", 0.05);
  const dataSource = q.get("data_source") ?? "sample";
  const symbol = q.get("symbol") ?? "BTC/USDT";
  const timeframe = q.get("timeframe") ?? "1h";
  const limit = num(q, "limit", 350);

  try {
    if (path === "/api/health")
      return json({ ok: true, service: "crypto-auto-trade", strategy_count: strategyNames().length, exchange_count: VENUES.length });

    if (path === "/api/strategies") {
      const includeVariants = (q.get("include_variants") ?? "true") !== "false";
      return json({ strategies: strategyDescriptions(includeVariants), count: strategyNames().length });
    }

    if (path === "/api/exchanges") {
      const apiReadyOnly = q.get("api_ready_only") === "true";
      const venues = apiReadyOnly ? apiReadyVenues() : VENUES;
      return json({ exchanges: venues, count: venues.length });
    }

    if (path === "/api/backtest") {
      const strategy = q.get("strategy") ?? "regime_guard";
      const { candles } = await chooseCandles(dataSource, false, symbol, timeframe, limit);
      return json(runBacktest(strategy, candles, defaultConfig(trailing)));
    }

    if (path === "/api/forward-test") {
      const strategy = q.get("strategy") ?? "regime_guard";
      const { candles } = await chooseCandles(dataSource, false, symbol, timeframe, limit);
      return json(forwardTest(strategy, candles, defaultConfig(trailing)));
    }

    if (path === "/api/realtime") {
      const strategy = q.get("strategy") ?? "regime_guard";
      const live = q.get("live") === "true";
      const { candles, source } = await chooseCandles(dataSource, live, symbol, timeframe, limit);
      const result = runBacktest(strategy, candles, defaultConfig(trailing)) as unknown as Record<string, unknown>;
      result.source = source === "sample" ? "sample" : live ? "live" : "sample";
      result.symbol = symbol;
      result.timeframe = timeframe;
      return json(result);
    }

    if (path === "/api/compare") {
      const { candles } = await chooseCandles(dataSource, false, symbol, timeframe, limit);
      return json({ backtest: compareAllStrategies(candles, trailing), forward: forwardAllStrategies(candles, trailing) });
    }

    if (path === "/api/validate") {
      const iterations = Math.min(Math.max(1, num(q, "iterations", 300)), 600);
      const { candles } = await chooseCandles(dataSource, false, symbol, timeframe, limit);
      return json(runValidationMatrix(candles, iterations, trailing));
    }

    if (path === "/api/best-strategy") {
      const iterations = Math.min(Math.max(1, num(q, "iterations", 300)), 600);
      const { candles } = await chooseCandles(dataSource, false, symbol, timeframe, limit);
      return json(selectBestStrategy(candles, iterations, trailing));
    }

    if (path === "/api/verify-profitability") {
      const iterations = Math.min(Math.max(1, num(q, "iterations", 300)), 600);
      const { candles } = await chooseCandles(dataSource, false, symbol, timeframe, limit);
      return json(verifyProfitability(candles, trailing, iterations));
    }

    if (path === "/api/market/prices") {
      const vs = q.get("vs_currency") ?? "usd";
      const pages = Math.min(Math.max(1, num(q, "pages", 1)), 5);
      const perPage = Math.min(Math.max(1, num(q, "per_page", 100)), 250);
      const prices: unknown[] = [];
      for (let page = 1; page <= pages; page++) {
        const cg = `https://api.coingecko.com/api/v3/coins/markets?vs_currency=${encodeURIComponent(vs)}&order=market_cap_desc&per_page=${perPage}&page=${page}&sparkline=false`;
        const res = await fetch(cg, { headers: { accept: "application/json" } });
        if (!res.ok) break;
        const batch = (await res.json()) as unknown[];
        prices.push(...batch);
      }
      return json({ count: prices.length, path: null, note: "Live snapshot from CoinGecko (not persisted on Workers).", vs_currency: vs, prices });
    }

    if (path === "/api/simulations" && url.search === "")
      return json({ results: [], note: "5Y simulation result persistence is not available on Workers (no filesystem)." });

    return json({ error: "not found", path }, 404);
  } catch (err) {
    return json({ error: String(err instanceof Error ? err.message : err) }, 400);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path.startsWith("/api/")) return handleApi(url);

    // Static dashboard. The asset server resolves "/" to index.html via its
    // default html_handling, so pass the request straight through. The HTML
    // references /static/<file>, which we remap to the asset directory root.
    if (path.startsWith("/static/")) return env.ASSETS.fetch(new Request(new URL(path.replace("/static/", "/"), url), request));
    return env.ASSETS.fetch(request);
  },
};
