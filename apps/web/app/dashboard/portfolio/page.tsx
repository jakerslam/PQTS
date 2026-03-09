import { getAccountSummary, getPositions } from "@/lib/api/client";

export default async function PortfolioPage() {
  const [account, positions] = await Promise.all([getAccountSummary(), getPositions()]).catch(
    () => [null, []],
  );

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <div className="grid">
        <article className="card">
          <p className="kpi-title">Equity</p>
          <p className="kpi-value">{account ? `$${account.equity.toFixed(2)}` : "Unavailable"}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Buying Power</p>
          <p className="kpi-value">{account ? `$${account.buying_power.toFixed(2)}` : "Unavailable"}</p>
        </article>
        <article className="card">
          <p className="kpi-title">Cash</p>
          <p className="kpi-value">{account ? `$${account.cash.toFixed(2)}` : "Unavailable"}</p>
        </article>
      </div>

      <article className="card">
        <h2 style={{ marginTop: 0 }}>Open Positions</h2>
        {positions.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>No position rows available from API.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Symbol</th>
                <th align="right">Qty</th>
                <th align="right">Avg</th>
                <th align="right">Mark</th>
                <th align="right">Unrealized PnL</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((row) => (
                <tr key={row.symbol}>
                  <td>{row.symbol}</td>
                  <td align="right">{row.qty.toFixed(4)}</td>
                  <td align="right">{row.avg_price.toFixed(4)}</td>
                  <td align="right">{row.market_price.toFixed(4)}</td>
                  <td align="right">{row.unrealized_pnl.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>
    </section>
  );
}
