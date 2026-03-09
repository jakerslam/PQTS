import Link from "next/link";
import { ToolEventRenderer } from "@/components/tool-renderers/tool-event-renderer";
import { getRegisteredToolTypes } from "@/lib/tools/registry";

export default function DashboardHomePage() {
  const knownTypes = getRegisteredToolTypes();
  return (
    <section style={{ display: "grid", gap: 16 }}>
      <div className="grid">
        <article className="card">
          <h3>Portfolio</h3>
          <p>Account equity, exposure, and attribution panels.</p>
          <Link href="/dashboard/portfolio">Open portfolio view</Link>
        </article>
        <article className="card">
          <h3>Execution</h3>
          <p>Orders, fills, and execution quality telemetry.</p>
          <Link href="/dashboard/execution">Open execution view</Link>
        </article>
        <article className="card">
          <h3>Risk</h3>
          <p>Kill-switch events, drawdown, and guardrails.</p>
          <Link href="/dashboard/risk">Open risk view</Link>
        </article>
      </div>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Tool Renderer Registry</h3>
        <p>Registered tool types: {knownTypes.join(", ")}</p>
      </article>

      <ToolEventRenderer
        event={{
          toolType: "risk_state",
          status: "complete",
          payload: { kill_switch_active: false, kill_switch_reason: "" },
        }}
      />
      <ToolEventRenderer
        event={{
          toolType: "unknown_tool",
          status: "complete",
          payload: { sample: true },
        }}
      />
    </section>
  );
}
