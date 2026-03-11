import Link from "next/link";
import { getAccountSummary, getRiskState } from "@/lib/api/client";

export default async function HomePage() {
  const [account, risk] = await Promise.all([getAccountSummary(), getRiskState()]).catch(() => [null, null]);

  return (
    <main>
      <section className="card">
        <h1 style={{ marginTop: 0 }}>PQTS Studio</h1>
        <p style={{ margin: 0, color: "var(--muted)" }}>
          Web-primary control tower for strategy operations, risk gates, and promotion evidence.
        </p>
      </section>

      <section className="grid" style={{ marginTop: 16 }}>
        <article className="card">
          <p className="kpi-title">Equity</p>
          <p className="kpi-value">{account ? `$${account.equity.toFixed(2)}` : "Unavailable"}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Cash</p>
          <p className="kpi-value">{account ? `$${account.cash.toFixed(2)}` : "Unavailable"}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Kill Switch</p>
          <p className="kpi-value">{risk?.kill_switch_active ? "ACTIVE" : "NORMAL"}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Daily PnL</p>
          <p className="kpi-value">{risk ? `$${risk.daily_pnl.toFixed(2)}` : "Unavailable"}</p>
        </article>
      </section>

      <section className="card" style={{ marginTop: 16 }}>
        <h2 style={{ marginTop: 0 }}>Start Flow</h2>
        <p style={{ marginBottom: 0, color: "var(--muted)" }}>
          Complete guided onboarding, then move into dashboard execution/risk surfaces with one shared data model.
        </p>
        <div style={{ marginTop: 12, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link href="/onboarding">Guided onboarding</Link>
          <Link href="/dashboard">Open Studio dashboard</Link>
        </div>
      </section>
    </main>
  );
}
