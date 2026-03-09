import { getFills, getOrders } from "@/lib/api/client";

export default async function ExecutionPage() {
  const [orders, fills] = await Promise.all([getOrders(), getFills()]).catch(() => [[], []]);

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        <h2 style={{ marginTop: 0 }}>Orders</h2>
        {orders.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>No orders available from API.</p>
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
          <p style={{ color: "var(--muted)" }}>No fills available from API.</p>
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
