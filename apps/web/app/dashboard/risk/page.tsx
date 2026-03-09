import { getRiskState } from "@/lib/api/client";

export default async function RiskPage() {
  const risk = await getRiskState().catch(() => null);

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        <h2 style={{ marginTop: 0 }}>Risk State</h2>
        {risk ? (
          <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "220px 1fr", rowGap: 8 }}>
            <dt>Kill Switch</dt>
            <dd>{risk.kill_switch_active ? "ACTIVE" : "Normal"}</dd>
            <dt>Reason</dt>
            <dd>{risk.kill_switch_reason || "None"}</dd>
            <dt>Current Drawdown</dt>
            <dd>{(risk.current_drawdown * 100).toFixed(2)}%</dd>
            <dt>Daily PnL</dt>
            <dd>${risk.daily_pnl.toFixed(2)}</dd>
          </dl>
        ) : (
          <p style={{ color: "var(--muted)" }}>Risk endpoint unavailable.</p>
        )}
      </article>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Alerts Panel (Initial)</h3>
        <p style={{ marginBottom: 0, color: "var(--muted)" }}>
          This panel is wired to current risk state and will expand with streaming incidents in PQTS-033.
        </p>
      </article>
    </section>
  );
}
