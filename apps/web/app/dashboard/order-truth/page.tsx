import Link from "next/link";

import { ProvenanceDrawer } from "@/components/provenance/provenance-drawer";
import { getOrderTruth, getReferencePerformance } from "@/lib/api/client";

interface PageProps {
  searchParams?: {
    order_id?: string;
  };
}

export default async function OrderTruthPage({ searchParams }: PageProps) {
  const orderId = String(searchParams?.order_id ?? "").trim();
  const [payload, reference] = await Promise.all([
    getOrderTruth(orderId).catch(() => ({ selected: null, rows: [], explanation: [], evidence_bundle: null })),
    getReferencePerformance().catch(() => null),
  ]);
  const provenance = reference?.provenance;

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        {provenance ? (
          <ProvenanceDrawer provenance={provenance} title="Order truth provenance" />
        ) : (
          <p style={{ margin: 0, color: "var(--muted)" }}>
            Provenance unavailable. This indicates missing benchmark artifacts or API connectivity.
          </p>
        )}
      </article>
      <article className="card" style={{ display: "grid", gap: 8 }}>
        <h2 style={{ margin: 0 }}>Per-Order Truth Drilldown</h2>
        {payload.evidence_bundle ? (
          <div style={{ padding: 10, border: "1px solid var(--border)" }}>
            <strong>Event-Intel Evidence Bundle</strong>
            <p style={{ margin: "6px 0 0 0", color: "var(--muted)" }}>
              trust={payload.evidence_bundle.trust_label} · sources={payload.evidence_bundle.source_count} ·
              causal={payload.evidence_bundle.causal_ok ? "ok" : "fail"} · expected_net_ev=
              {payload.evidence_bundle.expected_net_ev.toFixed(4)}
            </p>
          </div>
        ) : null}
        {payload.selected ? (
          <>
            <p style={{ margin: 0 }}>
              Selected order: <strong>{payload.selected.trade_id}</strong> ({payload.selected.strategy_id})
            </p>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {payload.explanation.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "220px 1fr", rowGap: 8 }}>
              <dt>Symbol</dt>
              <dd>{payload.selected.symbol}</dd>
              <dt>Venue</dt>
              <dd>{payload.selected.exchange}</dd>
              <dt>Side</dt>
              <dd>{payload.selected.side}</dd>
              <dt>Qty</dt>
              <dd>{payload.selected.quantity.toFixed(4)}</dd>
              <dt>Price</dt>
              <dd>{payload.selected.price.toFixed(4)}</dd>
              <dt>Realized Slippage</dt>
              <dd>{payload.selected.realized_slippage_bps.toFixed(3)} bps</dd>
              <dt>Predicted Slippage</dt>
              <dd>{payload.selected.predicted_slippage_bps.toFixed(3)} bps</dd>
              <dt>Net Alpha</dt>
              <dd>{payload.selected.realized_net_alpha_usd.toFixed(4)} USD</dd>
            </dl>
          </>
        ) : (
          <p style={{ margin: 0, color: "var(--muted)" }}>No execution-quality rows available.</p>
        )}
      </article>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Recent Orders</h3>
        {payload.rows.length === 0 ? (
          <p style={{ margin: 0, color: "var(--muted)" }}>No order truth rows available.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Order</th>
                <th align="left">Strategy</th>
                <th align="left">Symbol</th>
                <th align="right">Slip (bps)</th>
                <th align="right">Net Alpha</th>
                <th align="left">Inspect</th>
              </tr>
            </thead>
            <tbody>
              {payload.rows.slice(0, 80).map((row) => (
                <tr key={`${row.trade_id}:${row.timestamp}`}>
                  <td>{row.trade_id}</td>
                  <td>{row.strategy_id}</td>
                  <td>{row.symbol}</td>
                  <td align="right">{row.realized_slippage_bps.toFixed(3)}</td>
                  <td align="right">{row.realized_net_alpha_usd.toFixed(4)}</td>
                  <td>
                    <Link href={`/dashboard/order-truth?order_id=${encodeURIComponent(row.trade_id)}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>
    </section>
  );
}
