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
    </main>
  );
}
