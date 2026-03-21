import { getRiskState } from "@/lib/api/client";
import { OperatorActionPanel } from "@/components/operator/operator-action-panel";
import { LiveStreamStatus } from "@/components/stream/live-stream-status";
import { listBlockReasonEntries } from "@/lib/ops/block-reasons";

export default async function RiskPage() {
  const risk = await getRiskState().catch(() => null);
  const blockReasons = listBlockReasonEntries();

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        <h2 style={{ marginTop: 0 }}>Risk State</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <LiveStreamStatus channel="risk" />
        </div>
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
          <p style={{ color: "var(--muted)" }}>
            Risk endpoint unavailable. This indicates degraded connectivity or backend state, not a healthy zero-risk state.
          </p>
        )}
      </article>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Alerts Panel (Initial)</h3>
        <p style={{ marginBottom: 0, color: "var(--muted)" }}>
          This panel is wired to current risk state and will expand with streaming incidents in PQTS-033.
        </p>
      </article>
      <article className="card">
        <h3 style={{ marginTop: 0 }}>Block Reason Explainers</h3>
        <p style={{ marginTop: 0, color: "var(--muted)" }}>
          Human-readable gate outcomes for operators and beginner onboarding support.
        </p>
        <div className="grid">
          {blockReasons.map((row) => (
            <article key={row.code} className="card card-subtle">
              <p style={{ margin: "0 0 6px", fontWeight: 700 }}>{row.code}</p>
              <p style={{ margin: 0, color: "var(--muted)" }}>{row.explanation}</p>
            </article>
          ))}
        </div>
      </article>
      <OperatorActionPanel />
    </section>
  );
}
