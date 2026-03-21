import Link from "next/link";

import { TradeTicket } from "@/components/trading/trade-ticket";
import {
  getAccountSummary,
  getExecutionQuality,
  getFills,
  getOrders,
  getPnLSnapshots,
  getPositions,
  getPromotions,
  getReferencePerformance,
  getRiskState,
} from "@/lib/api/client";

interface Candle {
  bucket: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface SparkPoint {
  x: number;
  y: number;
}

function formatUsd(value: number): string {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatSignedPct(value: number): string {
  const pct = value * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
}

function formatTime(value: string): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.slice(11, 19) || value;
  }
  return parsed.toISOString().slice(11, 19);
}

function minuteBucket(timestamp: string): string {
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) {
    return timestamp.slice(0, 16);
  }
  return parsed.toISOString().slice(0, 16);
}

function linePoints(values: number[], width: number, height: number, padding = 14): SparkPoint[] {
  if (values.length <= 1) {
    return [];
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1e-9);
  const xSpan = Math.max(width - padding * 2, 1);
  const ySpan = Math.max(height - padding * 2, 1);
  return values.map((value, index) => {
    const x = padding + (index / Math.max(values.length - 1, 1)) * xSpan;
    const normalized = (value - min) / span;
    const y = height - padding - normalized * ySpan;
    return { x, y };
  });
}

function toPolyline(points: SparkPoint[]): string {
  return points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
}

function buildCandles(
  fills: Array<{ timestamp: string; price: number; quantity: number }>,
  limit = 60,
): Candle[] {
  if (fills.length === 0) {
    return [];
  }
  const byBucket = new Map<string, Candle>();
  const sorted = fills
    .slice()
    .sort((left, right) => String(left.timestamp).localeCompare(String(right.timestamp)));
  for (const fill of sorted) {
    const bucket = minuteBucket(fill.timestamp);
    const price = Number(fill.price);
    const qty = Number(fill.quantity);
    if (!Number.isFinite(price) || price <= 0 || !Number.isFinite(qty)) {
      continue;
    }
    const existing = byBucket.get(bucket);
    if (!existing) {
      byBucket.set(bucket, {
        bucket,
        open: price,
        high: price,
        low: price,
        close: price,
        volume: Math.max(qty, 0),
      });
      continue;
    }
    existing.high = Math.max(existing.high, price);
    existing.low = Math.min(existing.low, price);
    existing.close = price;
    existing.volume += Math.max(qty, 0);
  }
  return Array.from(byBucket.values())
    .sort((left, right) => left.bucket.localeCompare(right.bucket))
    .slice(-limit);
}

function strategySharpeProxy(values: number[]): number {
  if (values.length < 2) {
    return 0;
  }
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1);
  const std = Math.sqrt(Math.max(variance, 1e-12));
  return (mean / std) * Math.sqrt(values.length);
}

export default async function DashboardHomePage() {
  const [account, risk, positions, orders, fills, pnlRows, executionQuality, promotions, references] =
    await Promise.all([
      getAccountSummary().catch(() => null),
      getRiskState().catch(() => null),
      getPositions().catch(() => []),
      getOrders().catch(() => []),
      getFills().catch(() => []),
      getPnLSnapshots(400).catch(() => []),
      getExecutionQuality(350).catch(() => []),
      getPromotions().catch(() => []),
      getReferencePerformance().catch(() => ({
        generated_at: "",
        bundle_count: 0,
        bundles: [],
        provenance: undefined,
      })),
    ]);

  const netPnlSeries = pnlRows.map((row) => Number(row.net_pnl)).filter((value) => Number.isFinite(value));
  const netPnlPoints = linePoints(netPnlSeries, 920, 300);
  const candles = buildCandles(
    fills.map((fill) => ({
      timestamp: String(fill.timestamp),
      price: Number(fill.price),
      quantity: Number(fill.quantity),
    })),
  );

  const today = new Date().toISOString().slice(0, 10);
  const todayOrders = orders.filter((row) => String(row.created_at).slice(0, 10) === today).length;
  const grossExposure = positions.reduce(
    (sum, row) => sum + Math.abs(Number(row.qty) * Number(row.market_price)),
    0,
  );
  const exposurePct = account && account.equity > 0 ? grossExposure / account.equity : 0;

  const latestPnl = netPnlSeries.length > 0 ? netPnlSeries[netPnlSeries.length - 1] : Number(risk?.daily_pnl ?? 0);
  const previousPnl = netPnlSeries.length > 1 ? netPnlSeries[netPnlSeries.length - 2] : 0;
  const pnlDelta = latestPnl - previousPnl;
  const portfolioChange = account && account.equity > 0 ? pnlDelta / account.equity : 0;

  const wins = executionQuality.filter((row) => Number(row.realized_net_alpha_usd) > 0).length;
  const winRate = executionQuality.length > 0 ? wins / executionQuality.length : 0;

  const bestBundle =
    references.bundles.length > 0
      ? references.bundles
          .slice()
          .sort((left, right) => {
            if (right.summary.avg_quality_score !== left.summary.avg_quality_score) {
              return right.summary.avg_quality_score - left.summary.avg_quality_score;
            }
            return right.summary.avg_fill_rate - left.summary.avg_fill_rate;
          })[0]
      : null;

  const optimizationTarget =
    references.bundles.length > 0
      ? references.bundles
          .slice()
          .sort((left, right) => right.summary.avg_reject_rate - left.summary.avg_reject_rate)[0]
      : null;

  const recentFills = fills
    .slice()
    .sort((left, right) => String(right.timestamp).localeCompare(String(left.timestamp)))
    .slice(0, 14);

  const orderSideById = new Map(orders.map((order) => [order.order_id, order.side]));

  const strategyMap = new Map<
    string,
    {
      stage: string;
      allocation: number;
      pnl: number;
      slippage: number[];
      alpha: number[];
      samples: number;
    }
  >();
  for (const promotion of promotions) {
    strategyMap.set(promotion.strategy_id, {
      stage: promotion.stage,
      allocation: promotion.capital_allocation_pct,
      pnl: 0,
      slippage: [],
      alpha: [],
      samples: 0,
    });
  }
  for (const row of executionQuality) {
    const key = row.strategy_id || "unknown";
    const current =
      strategyMap.get(key) ??
      ({
        stage: "paper",
        allocation: 0,
        pnl: 0,
        slippage: [],
        alpha: [],
        samples: 0,
      } as const);
    const next = {
      ...current,
      pnl: current.pnl + Number(row.realized_net_alpha_usd),
      slippage: [...current.slippage, Number(row.realized_slippage_bps)],
      alpha: [...current.alpha, Number(row.realized_net_alpha_usd)],
      samples: current.samples + 1,
    };
    strategyMap.set(key, next);
  }
  const strategyRows = Array.from(strategyMap.entries())
    .map(([strategy, stats]) => ({
      strategy,
      stage: stats.stage,
      allocation: stats.allocation,
      samples: stats.samples,
      avgSlippage:
        stats.slippage.length > 0
          ? stats.slippage.reduce((sum, value) => sum + value, 0) / stats.slippage.length
          : 0,
      pnl: stats.pnl,
      sharpeProxy: strategySharpeProxy(stats.alpha),
    }))
    .sort((left, right) => right.pnl - left.pnl)
    .slice(0, 10);

  const candleLow = candles.length > 0 ? Math.min(...candles.map((row) => row.low)) : 0;
  const candleHigh = candles.length > 0 ? Math.max(...candles.map((row) => row.high)) : 0;
  const candleSpan = Math.max(candleHigh - candleLow, 1e-9);
  const maxVolume = candles.length > 0 ? Math.max(...candles.map((row) => row.volume), 1e-9) : 1;

  return (
    <section className="terminal-grid">
      <section className="summary-row">
        <article className="card kpi-card">
          <p className="kpi-title">Portfolio Value</p>
          <p className="kpi-value">{account ? formatUsd(account.equity) : "Unavailable"}</p>
          <p className={portfolioChange >= 0 ? "metric-positive" : "metric-negative"}>
            {formatSignedPct(portfolioChange)}
          </p>
        </article>
        <article className="card kpi-card">
          <p className="kpi-title">Today&apos;s PnL</p>
          <p className="kpi-value">{formatUsd(pnlDelta)}</p>
          <p>{todayOrders} orders</p>
        </article>
        <article className="card kpi-card">
          <p className="kpi-title">Open Positions</p>
          <p className="kpi-value">{positions.length}</p>
          <p>{formatSignedPct(exposurePct)} gross exposure</p>
        </article>
        <article className="card kpi-card">
          <p className="kpi-title">Win Rate</p>
          <p className="kpi-value">{(winRate * 100).toFixed(1)}%</p>
          <p>{executionQuality.length} qualified fills</p>
        </article>
        <article className="card kpi-card">
          <p className="kpi-title">Best Sim Quality</p>
          <p className="kpi-value">{bestBundle ? bestBundle.summary.avg_quality_score.toFixed(3) : "0.000"}</p>
          <p>{bestBundle ? bestBundle.bundle : "No bundle"}</p>
        </article>
        <article className="card kpi-card">
          <p className="kpi-title">Optimization Target</p>
          <p className="kpi-value">
            {optimizationTarget ? optimizationTarget.summary.avg_reject_rate.toFixed(3) : "0.000"}
          </p>
          <p>{optimizationTarget ? optimizationTarget.bundle : "No bundle"}</p>
        </article>
      </section>

      <section className="desk-grid-two">
        <div className="desk-column">
          <article className="chart-container">
            <div className="panel-header">
              <h3>Equity Curve</h3>
              <span className="status-chip">samples:{netPnlSeries.length}</span>
            </div>
            <p className="panel-subtitle">Net PnL snapshots from the active account.</p>
            {netPnlPoints.length > 1 ? (
              <svg viewBox="0 0 920 300" className="chart-svg" role="img" aria-label="Equity curve">
                <polyline
                  points={toPolyline(netPnlPoints)}
                  fill="none"
                  stroke="var(--chart-1)"
                  strokeWidth={3}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <p className="empty-state">No PnL history available.</p>
            )}
          </article>

          <article className="chart-container">
            <div className="panel-header">
              <h3>Price Tape (Candles)</h3>
              <span className="status-chip">fills:{fills.length}</span>
            </div>
            <p className="panel-subtitle">Minute candles synthesized from execution fill prices.</p>
            {candles.length > 2 ? (
              <div className="candle-shell">
                <svg viewBox="0 0 920 280" className="chart-svg" role="img" aria-label="Price candles">
                  {candles.map((candle, index) => {
                    const slot = 920 / candles.length;
                    const center = slot * index + slot / 2;
                    const bodyWidth = Math.max(slot * 0.62, 2);
                    const yHigh = 14 + ((candleHigh - candle.high) / candleSpan) * 250;
                    const yLow = 14 + ((candleHigh - candle.low) / candleSpan) * 250;
                    const yOpen = 14 + ((candleHigh - candle.open) / candleSpan) * 250;
                    const yClose = 14 + ((candleHigh - candle.close) / candleSpan) * 250;
                    const top = Math.min(yOpen, yClose);
                    const bodyHeight = Math.max(Math.abs(yClose - yOpen), 1.6);
                    const up = candle.close >= candle.open;
                    return (
                      <g key={candle.bucket}>
                        <line
                          x1={center}
                          x2={center}
                          y1={yHigh}
                          y2={yLow}
                          stroke={up ? "var(--chart-up)" : "var(--chart-down)"}
                          strokeWidth={1.2}
                        />
                        <rect
                          x={center - bodyWidth / 2}
                          y={top}
                          width={bodyWidth}
                          height={bodyHeight}
                          fill={up ? "rgba(25, 201, 154, 0.85)" : "rgba(255, 99, 125, 0.88)"}
                        />
                      </g>
                    );
                  })}
                </svg>
                <svg viewBox="0 0 920 90" className="volume-svg" role="img" aria-label="Volume bars">
                  {candles.map((candle, index) => {
                    const slot = 920 / candles.length;
                    const width = Math.max(slot * 0.62, 1.8);
                    const x = slot * index + slot / 2 - width / 2;
                    const height = (candle.volume / maxVolume) * 82;
                    const y = 88 - height;
                    return (
                      <rect
                        key={`${candle.bucket}:volume`}
                        x={x}
                        y={y}
                        width={width}
                        height={height}
                        fill="rgba(105, 139, 201, 0.72)"
                      />
                    );
                  })}
                </svg>
              </div>
            ) : (
              <p className="empty-state">Not enough fills to build candle series.</p>
            )}
          </article>
        </div>

        <div className="desk-column">
          <TradeTicket defaultSymbol={orders[0]?.symbol || "BTCUSDT"} />

          <article className="table-container">
            <h3>Open Positions</h3>
            {positions.length === 0 ? (
              <p className="empty-state">No open positions.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>Avg</th>
                    <th>Mark</th>
                    <th>Unrealized PnL</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.slice(0, 12).map((row) => (
                    <tr key={row.symbol}>
                      <td>{row.symbol}</td>
                      <td>{row.qty.toFixed(4)}</td>
                      <td>{row.avg_price.toFixed(4)}</td>
                      <td>{row.market_price.toFixed(4)}</td>
                      <td className={row.unrealized_pnl >= 0 ? "metric-positive" : "metric-negative"}>
                        {row.unrealized_pnl.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>

          <article className="table-container">
            <h3>Recent Trades</h3>
            {recentFills.length === 0 ? (
              <p className="empty-state">No fills recorded.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Qty</th>
                    <th>Price</th>
                    <th>Net Alpha</th>
                  </tr>
                </thead>
                <tbody>
                  {recentFills.map((row) => {
                    const quality = executionQuality.find((item) => item.trade_id === row.fill_id);
                    const side = orderSideById.get(row.order_id) || "n/a";
                    const alpha = quality?.realized_net_alpha_usd ?? 0;
                    return (
                      <tr key={row.fill_id}>
                        <td>{formatTime(String(row.timestamp))}</td>
                        <td>{row.symbol}</td>
                        <td>{String(side).toUpperCase()}</td>
                        <td>{row.quantity.toFixed(4)}</td>
                        <td>{row.price.toFixed(4)}</td>
                        <td className={alpha >= 0 ? "metric-positive" : "metric-negative"}>{alpha.toFixed(4)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </article>
        </div>
      </section>

      <section className="desk-grid-two">
        <article className="table-container">
          <h3>Strategy Performance</h3>
          {strategyRows.length === 0 ? (
            <p className="empty-state">No strategy metrics available.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Stage</th>
                  <th>Alloc %</th>
                  <th>Samples</th>
                  <th>Sharpe*</th>
                  <th>Avg Slip (bps)</th>
                  <th>Net Alpha</th>
                </tr>
              </thead>
              <tbody>
                {strategyRows.map((row) => (
                  <tr key={row.strategy}>
                    <td>{row.strategy}</td>
                    <td>{row.stage}</td>
                    <td>{row.allocation.toFixed(2)}</td>
                    <td>{row.samples}</td>
                    <td>{row.sharpeProxy.toFixed(2)}</td>
                    <td>{row.avgSlippage.toFixed(3)}</td>
                    <td className={row.pnl >= 0 ? "metric-positive" : "metric-negative"}>{row.pnl.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="panel-footnote">*Sharpe proxy uses realized net-alpha sample distribution.</p>
        </article>

        <article className="table-container">
          <h3>Simulation Leaderboard</h3>
          {references.bundles.length === 0 ? (
            <p className="empty-state">No reference bundles published yet.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Bundle</th>
                  <th>Markets</th>
                  <th>Strategies</th>
                  <th>Fill</th>
                  <th>Reject</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {references.bundles.slice(0, 10).map((bundle) => (
                  <tr key={bundle.bundle}>
                    <td>{bundle.bundle}</td>
                    <td>{bundle.markets}</td>
                    <td>{bundle.strategies}</td>
                    <td>{bundle.summary.avg_fill_rate.toFixed(3)}</td>
                    <td>{bundle.summary.avg_reject_rate.toFixed(3)}</td>
                    <td>{bundle.summary.avg_quality_score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </article>
      </section>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Quick Views</h3>
        <div className="quick-links">
          <Link href="/dashboard/execution">Execution Console</Link>
          <Link href="/dashboard/risk">Risk Controls</Link>
          <Link href="/dashboard/promotion">Promotion Gates</Link>
          <Link href="/dashboard/order-truth">Order Truth</Link>
          <Link href="/dashboard/replay">Replay</Link>
          <Link href="/dashboard/benchmarks">Benchmarks</Link>
        </div>
      </article>
    </section>
  );
}
