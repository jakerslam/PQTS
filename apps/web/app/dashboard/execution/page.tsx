import { ProvenanceDrawer } from "@/components/provenance/provenance-drawer";
import { getFills, getOrderTruth, getOrders, getReferencePerformance } from "@/lib/api/client";
import { LiveStreamStatus } from "@/components/stream/live-stream-status";
import { TradeTicket } from "@/components/trading/trade-ticket";
import Link from "next/link";

export default async function ExecutionPage() {
  const [orders, fills, truth, references] = await Promise.all([
    getOrders().catch(() => []),
    getFills().catch(() => []),
    getOrderTruth().catch(() => ({
      selected: null,
      rows: [],
      explanation: [],
      evidence_bundle: null,
      decision_card: null,
    })),
    getReferencePerformance().catch(() => null),
  ]);

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        <h2 style={{ marginTop: 0 }}>Execution Analytics</h2>
        <p style={{ marginTop: 0, color: "var(--muted)" }}>
          Deep-dive surfaces for transaction-cost quality and order truth lineage.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          <LiveStreamStatus channel="orders" />
          <LiveStreamStatus channel="fills" />
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link href="/dashboard/execution-quality">Execution Quality Dashboard</Link>
          <Link href="/dashboard/order-truth">Per-Order Truth Drilldown</Link>
          <Link href="/dashboard/replay">Deterministic Replay Timeline</Link>
        </div>
      </article>
      <TradeTicket defaultSymbol={orders[0]?.symbol || "BTCUSDT"} />
      <article className="card">
        {references?.provenance ? (
          <ProvenanceDrawer provenance={references.provenance} title="Execution provenance" />
        ) : (
          <p style={{ margin: 0, color: "var(--muted)" }}>
            Execution provenance unavailable; check benchmark artifact publication and API connectivity.
          </p>
        )}
      </article>

      <article className="card">
        <h2 style={{ marginTop: 0 }}>Order Lifecycle Explainability</h2>
        {truth.evidence_bundle ? (
          <div style={{ marginBottom: 12, padding: 10, border: "1px solid var(--border)" }}>
            <strong>Event-Intel Evidence</strong>
            <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 6 }}>
              trust={truth.evidence_bundle.trust_label} · sources={truth.evidence_bundle.source_count} ·
              gate={truth.evidence_bundle.risk_gate_decision} · latency=
              {truth.evidence_bundle.latency_ms.toFixed(1)}ms
            </div>
          </div>
        ) : null}
        {truth.decision_card ? (
          <div style={{ marginBottom: 12, padding: 10, border: "1px solid var(--border)" }}>
            <strong>Decision Card</strong>
            <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 6 }}>
              model={truth.decision_card.p_model.toFixed(4)} · market={truth.decision_card.p_market.toFixed(4)} ·
              net_edge={truth.decision_card.net_edge_bps.toFixed(2)}bps · gate=
              {truth.decision_card.gate_passed ? "passed" : "blocked"}
            </div>
          </div>
        ) : null}
        {truth.rows.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>No explainability rows available from order truth API.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Order</th>
                <th align="left">Signal</th>
                <th align="left">Risk Gate</th>
                <th align="left">Router/Venue</th>
                <th align="left">Fill Outcome</th>
                <th align="left">Drilldown</th>
              </tr>
            </thead>
            <tbody>
              {truth.rows.slice(0, 12).map((row) => {
                const riskDecision =
                  row.realized_net_alpha_usd > 0
                    ? "ALLOW"
                    : row.predicted_slippage_bps > row.realized_slippage_bps
                      ? "REDUCE"
                      : "HOLD";
                const outcome =
                  row.realized_slippage_bps <= row.predicted_slippage_bps
                    ? `within budget (${row.realized_slippage_bps.toFixed(2)}bps)`
                    : `drifted (${row.realized_slippage_bps.toFixed(2)}bps)`;
                return (
                  <tr key={row.trade_id}>
                    <td>{row.trade_id}</td>
                    <td>{row.strategy_id}</td>
                    <td>{riskDecision}</td>
                    <td>
                      {row.exchange} · {row.side}
                    </td>
                    <td>{outcome}</td>
                    <td>
                      <Link href={`/dashboard/order-truth?order_id=${encodeURIComponent(row.trade_id)}`}>Open</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </article>

      <article className="card">
        <h2 style={{ marginTop: 0 }}>Orders</h2>
        {orders.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>
            No orders available from API. This is an explicit empty/disconnected state, not synthetic demo data.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Order ID</th>
                <th align="left">Symbol</th>
                <th align="left">Side</th>
                <th align="right">Qty</th>
                <th align="left">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.slice(0, 25).map((row) => (
                <tr key={row.order_id}>
                  <td>{row.order_id}</td>
                  <td>{row.symbol}</td>
                  <td>{row.side}</td>
                  <td align="right">{row.quantity.toFixed(4)}</td>
                  <td>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>

      <article className="card">
        <h2 style={{ marginTop: 0 }}>Recent Fills</h2>
        {fills.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>
            No fills available from API. This is an explicit empty/disconnected state, not synthetic demo data.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Fill ID</th>
                <th align="left">Order ID</th>
                <th align="left">Symbol</th>
                <th align="right">Qty</th>
                <th align="right">Price</th>
                <th align="left">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {fills.slice(0, 25).map((row) => (
                <tr key={row.fill_id}>
                  <td>{row.fill_id}</td>
                  <td>{row.order_id}</td>
                  <td>{row.symbol}</td>
                  <td align="right">{row.quantity.toFixed(4)}</td>
                  <td align="right">{row.price.toFixed(4)}</td>
                  <td>{row.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>
    </section>
  );
}
