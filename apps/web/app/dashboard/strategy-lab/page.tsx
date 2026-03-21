import { listTemplateRunArtifacts } from "@/lib/ops/template-gallery";

const TEMPLATE_CARDS = [
  {
    key: "momentum",
    title: "Momentum Template",
    conditions: "Trend continuation with stable liquidity.",
    risks: "Whipsaw regimes and stale quote entries.",
    successMetric: "Positive net alpha with stable fill rate.",
  },
  {
    key: "market_making",
    title: "Market Making Template",
    conditions: "Tight spreads with balanced order flow.",
    risks: "Adverse selection and toxic flow.",
    successMetric: "Spread capture net of fees and slippage.",
  },
  {
    key: "underdog_value",
    title: "Underdog Value Template",
    conditions: "Probability dislocations and bounded downside.",
    risks: "Model overconfidence and liquidity thin-outs.",
    successMetric: "EV-positive entry quality and reject discipline.",
  },
];

const KPI_DEFS = [
  ["Sharpe", "Risk-adjusted return. Higher is better when drawdown stays bounded."],
  ["Drawdown", "Peak-to-trough decline. Lower protects capital continuity."],
  ["Fill Rate", "Executed / submitted opportunities. Low values indicate venue friction."],
  ["Reject Rate", "Rejected / submitted opportunities. High values usually signal gating or routing issues."],
  ["Slippage", "Execution price drift vs reference. Lower is better."],
  ["Canary Ready Rate", "Share of runs meeting promotion gates toward canary/live."],
];

export default function StrategyLabPage() {
  const artifacts = listTemplateRunArtifacts(undefined, 12);
  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        <h2 style={{ marginTop: 0 }}>Strategy Lab</h2>
        <p style={{ marginTop: 0, color: "var(--muted)" }}>
          Guided templates for beginners with code-visible command artifacts for professionals.
        </p>
      </article>

      <div className="grid">
        {TEMPLATE_CARDS.map((card) => (
          <article key={card.key} className="card card-subtle">
            <h3 style={{ marginTop: 0 }}>{card.title}</h3>
            <p style={{ margin: "0 0 8px" }}>
              <strong>Best for:</strong> {card.conditions}
            </p>
            <p style={{ margin: "0 0 8px" }}>
              <strong>Primary risks:</strong> {card.risks}
            </p>
            <p style={{ margin: 0 }}>
              <strong>Success metric:</strong> {card.successMetric}
            </p>
          </article>
        ))}
      </div>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Metric Explainers</h3>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th align="left">Metric</th>
              <th align="left">Explanation</th>
            </tr>
          </thead>
          <tbody>
            {KPI_DEFS.map(([name, description]) => (
              <tr key={name}>
                <td>{name}</td>
                <td>{description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>GUI-to-Code Transparency</h3>
        {artifacts.length === 0 ? (
          <p style={{ margin: 0, color: "var(--muted)" }}>
            No template artifacts found yet. Run onboarding or `pqts quickstart --execute` first.
          </p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {artifacts.slice(0, 6).map((artifact) => (
              <li key={artifact.artifact_path}>
                <code>{artifact.command.join(" ")}</code>
                <span style={{ color: "var(--muted)" }}> → {artifact.artifact_path}</span>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
