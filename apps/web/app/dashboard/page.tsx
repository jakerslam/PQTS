import Link from "next/link";

import { StreamTurnPreview } from "@/components/stream/stream-turn-preview";
import { ToolEventRenderer } from "@/components/tool-renderers/tool-event-renderer";
import { ProvenanceDrawer } from "@/components/provenance/provenance-drawer";
import { getAccountSummary, getReferencePerformance, getRiskState } from "@/lib/api/client";
import { getRegisteredToolTypes } from "@/lib/tools/registry";

function nextActionHref(bundleCount: number, killSwitchActive: boolean): string {
  if (killSwitchActive) {
    return "/dashboard/risk";
  }
  if (bundleCount <= 0) {
    return "/onboarding";
  }
  return "/dashboard/promotion";
}

function nextActionLabel(bundleCount: number, killSwitchActive: boolean): string {
  if (killSwitchActive) {
    return "Review risk incidents";
  }
  if (bundleCount <= 0) {
    return "Run onboarding flow";
  }
  return "Review promotion gates";
}

export default async function DashboardHomePage() {
  const knownTypes = getRegisteredToolTypes();
  const [account, risk, references] = await Promise.all([
    getAccountSummary().catch(() => null),
    getRiskState().catch(() => null),
    getReferencePerformance().catch(() => ({
      generated_at: "",
      bundle_count: 0,
      bundles: [],
      provenance: undefined,
    })),
  ]);
  const bestBundle =
    references.bundles.length > 0
      ? references.bundles
          .slice()
          .sort((left, right) => {
            if (right.summary.avg_quality_score !== left.summary.avg_quality_score) {
              return right.summary.avg_quality_score - left.summary.avg_quality_score;
            }
            return right.summary.avg_fill_rate - left.summary.avg_fill_rate;
          })[0]
      : null;
  const killSwitchActive = Boolean(risk?.kill_switch_active);
  const actionHref = nextActionHref(references.bundle_count, killSwitchActive);
  const actionLabel = nextActionLabel(references.bundle_count, killSwitchActive);

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        <h2 style={{ marginTop: 0 }}>Command Center</h2>
        <div className="grid">
          <article className="card" style={{ background: "#f8fbff" }}>
            <p className="kpi-title">What is running now?</p>
            <p className="kpi-value">{references.bundle_count > 0 ? "Reference Bundles Active" : "No Published Bundle"}</p>
          </article>
          <article className="card" style={{ background: "#f8fbff" }}>
            <p className="kpi-title">Is it safe?</p>
            <p className="kpi-value">{killSwitchActive ? "Kill-Switch Active" : "Guardrails Normal"}</p>
          </article>
          <article className="card" style={{ background: "#f8fbff" }}>
            <p className="kpi-title">Capital snapshot</p>
            <p className="kpi-value">{account ? `$${account.equity.toFixed(2)} equity` : "Unavailable"}</p>
          </article>
          <article className="card" style={{ background: "#f8fbff" }}>
            <p className="kpi-title">What needs attention?</p>
            <p className="kpi-value">{actionLabel}</p>
            <Link href={actionHref}>Continue</Link>
          </article>
        </div>
        <p style={{ marginBottom: 0, color: "var(--muted)" }}>
          Promotion stage: {killSwitchActive ? "halt" : "paper/canary review"} · Benchmarks: {references.bundle_count}
        </p>
      </article>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Benchmark Reference Callout</h3>
        {bestBundle ? (
          <>
            <p style={{ margin: 0 }}>
              <strong>{bestBundle.bundle}</strong> · quality {bestBundle.summary.avg_quality_score.toFixed(3)} · fill{" "}
              {bestBundle.summary.avg_fill_rate.toFixed(3)} · reject {bestBundle.summary.avg_reject_rate.toFixed(3)} · trust{" "}
              <span className={`status-chip status-chip-${references.provenance?.trust_label ?? "unverified"}`}>
                {references.provenance?.trust_label ?? "unverified"}
              </span>
            </p>
            {references.provenance ? <ProvenanceDrawer provenance={references.provenance} /> : null}
          </>
        ) : (
          <p style={{ margin: 0, color: "var(--muted)" }}>No benchmark bundle available yet.</p>
        )}
      </article>

      <div className="grid">
        <article className="card">
          <h3>Onboarding</h3>
          <p>Generate CLI-first setup plans for beginner and pro operator profiles.</p>
          <Link href="/onboarding">Open onboarding wizard</Link>
        </article>
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
          <h3>Execution Quality</h3>
          <p>Reference-bundle slippage, alpha, and venue quality tape.</p>
          <Link href="/dashboard/execution-quality">Open quality dashboard</Link>
        </article>
        <article className="card">
          <h3>Order Truth</h3>
          <p>Signal-to-fill lineage and block/execution explanation per order.</p>
          <Link href="/dashboard/order-truth">Open order truth drilldown</Link>
        </article>
        <article className="card">
          <h3>Replay Timeline</h3>
          <p>Deterministic event-replay digest with hash and event-type stats.</p>
          <Link href="/dashboard/replay">Open replay timeline</Link>
        </article>
        <article className="card">
          <h3>Risk</h3>
          <p>Kill-switch events, drawdown, and guardrails.</p>
          <Link href="/dashboard/risk">Open risk view</Link>
        </article>
        <article className="card">
          <h3>Promotion</h3>
          <p>Stage-transition control center with explicit promotion actions.</p>
          <Link href="/dashboard/promotion">Open promotion control center</Link>
        </article>
        <article className="card">
          <h3>Templates</h3>
          <p>Generated template-run artifacts, config snapshots, and diffs.</p>
          <Link href="/dashboard/templates">Open template gallery</Link>
        </article>
        <article className="card">
          <h3>Notifications</h3>
          <p>Preview and execute stdout/Telegram/Discord channel checks.</p>
          <Link href="/dashboard/alerts">Open alerts view</Link>
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
      <StreamTurnPreview />
    </section>
  );
}
