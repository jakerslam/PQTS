import type { ToolRendererProps } from "@/lib/tools/types";

export function RiskStateToolCard({ event }: ToolRendererProps) {
  const payload = (event.payload ?? {}) as {
    kill_switch_active?: boolean;
    kill_switch_reason?: string;
  };
  return (
    <article className="card">
      <h3 style={{ marginTop: 0 }}>Risk State</h3>
      <p>Kill Switch: {payload.kill_switch_active ? "ACTIVE" : "Normal"}</p>
      <p style={{ marginBottom: 0 }}>Reason: {payload.kill_switch_reason || "None"}</p>
    </article>
  );
}
