import Link from "next/link";
import { getAccountSummary, getRiskState } from "@/lib/api/client";

export default async function HomePage() {
  const [account, risk] = await Promise.all([getAccountSummary(), getRiskState()]).catch(() => [null, null]);

  return (
    <main>
      <h1>PQTS Control Dashboard</h1>
      <p>Next.js web app scaffold is connected to the PQTS API contract layer.</p>

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
          <p className="kpi-value">{risk?.kill_switch_active ? "ACTIVE" : "Normal"}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Daily PnL</p>
          <p className="kpi-value">{risk ? `$${risk.daily_pnl.toFixed(2)}` : "Unavailable"}</p>
        </article>
      </section>

      <section className="card" style={{ marginTop: 16 }}>
        <h2 style={{ marginTop: 0 }}>New to PQTS?</h2>
        <p style={{ marginBottom: 0 }}>
          Start with the guided onboarding wizard, then continue into the authenticated dashboard.
        </p>
        <div style={{ marginTop: 12, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link href="/onboarding">Open onboarding wizard</Link>
          <Link href="/dashboard">Open dashboard</Link>
        </div>
      </section>
    </main>
  );
}
