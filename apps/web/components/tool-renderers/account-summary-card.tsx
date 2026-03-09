import type { ToolRendererProps } from "@/lib/tools/types";

export function AccountSummaryToolCard({ event }: ToolRendererProps) {
  const payload = (event.payload ?? {}) as {
    equity?: number;
    cash?: number;
    buying_power?: number;
  };
  return (
    <article className="card">
      <h3 style={{ marginTop: 0 }}>Account Snapshot</h3>
      <p>Equity: {payload.equity ?? "n/a"}</p>
      <p>Cash: {payload.cash ?? "n/a"}</p>
      <p style={{ marginBottom: 0 }}>Buying Power: {payload.buying_power ?? "n/a"}</p>
    </article>
  );
}
