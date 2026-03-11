import { ProvenanceDrawer } from "@/components/provenance/provenance-drawer";
import { getExecutionQuality, getReferencePerformance } from "@/lib/api/client";

function mean(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((total, value) => total + value, 0) / values.length;
}

export default async function ExecutionQualityPage() {
  const [rows, references] = await Promise.all([
    getExecutionQuality(250).catch(() => []),
    getReferencePerformance().catch(() => null),
  ]);
  const provenance = references?.provenance;
  const realized = rows.map((row) => row.realized_slippage_bps);
  const predicted = rows.map((row) => row.predicted_slippage_bps);
  const alpha = rows.map((row) => row.realized_net_alpha_usd);

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        {provenance ? (
          <ProvenanceDrawer provenance={provenance} title="Execution quality provenance" />
        ) : (
          <p style={{ margin: 0, color: "var(--muted)" }}>
            Provenance unavailable. Check reference bundle publication and API connectivity.
          </p>
        )}
      </article>
      <div className="grid">
        <article className="card">
          <p className="kpi-title">Rows</p>
          <p className="kpi-value">{rows.length}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Avg Realized Slippage (bps)</p>
          <p className="kpi-value">{mean(realized).toFixed(3)}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Avg Predicted Slippage (bps)</p>
          <p className="kpi-value">{mean(predicted).toFixed(3)}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Total Net Alpha (USD)</p>
          <p className="kpi-value">{alpha.reduce((total, value) => total + value, 0).toFixed(2)}</p>
        </article>
      </div>

      <article className="card">
        <h2 style={{ marginTop: 0 }}>Execution Quality Tape</h2>
        {rows.length === 0 ? (
          <p style={{ color: "var(--muted)", margin: 0 }}>
            No execution quality rows found in latest reference bundle.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Trade</th>
                <th align="left">Strategy</th>
                <th align="left">Symbol</th>
                <th align="left">Venue</th>
                <th align="right">Qty</th>
                <th align="right">Realized Slip (bps)</th>
                <th align="right">Predicted (bps)</th>
                <th align="right">Net Alpha (USD)</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 120).map((row) => (
                <tr key={`${row.trade_id}:${row.timestamp}`}>
                  <td>{row.trade_id}</td>
                  <td>{row.strategy_id}</td>
                  <td>{row.symbol}</td>
                  <td>{row.exchange}</td>
                  <td align="right">{row.quantity.toFixed(4)}</td>
                  <td align="right">{row.realized_slippage_bps.toFixed(3)}</td>
                  <td align="right">{row.predicted_slippage_bps.toFixed(3)}</td>
                  <td align="right">{row.realized_net_alpha_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>
    </section>
  );
}
