import { ProvenanceDrawer } from "@/components/provenance/provenance-drawer";
import { getReferencePerformance } from "@/lib/api/client";

function trustLabel(fillRate: number, quality: number): "reference" | "diagnostic_only" | "unverified" {
  if (fillRate > 0 && quality >= 0.25) return "reference";
  if (fillRate > 0) return "diagnostic_only";
  return "unverified";
}

export default async function BenchmarksPage() {
  const payload = await getReferencePerformance().catch(() => ({
    generated_at: "",
    bundle_count: 0,
    bundles: [],
    provenance: undefined,
  }));
  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        <h2 style={{ marginTop: 0 }}>Benchmarks and Results</h2>
        <p style={{ margin: "0 0 8px", color: "var(--muted)" }}>
          Above-the-fold evidence from published bundles with explicit trust classification and provenance.
        </p>
        <p style={{ margin: 0 }}>
          Last generated: <code>{payload.generated_at || "unknown"}</code>
        </p>
        {payload.provenance ? <ProvenanceDrawer provenance={payload.provenance} /> : null}
      </article>

      <article className="card">
        {payload.bundles.length === 0 ? (
          <p style={{ margin: 0, color: "var(--muted)" }}>
            No reference bundles found. Publish bundle artifacts under <code>results/</code>.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Bundle</th>
                <th align="left">Markets</th>
                <th align="left">Strategies</th>
                <th align="right">Fill</th>
                <th align="right">Reject</th>
                <th align="right">Quality</th>
                <th align="left">Trust</th>
                <th align="left">Provenance</th>
              </tr>
            </thead>
            <tbody>
              {payload.bundles.map((bundle) => {
                const label = trustLabel(bundle.summary.avg_fill_rate, bundle.summary.avg_quality_score);
                return (
                  <tr key={bundle.bundle}>
                    <td>{bundle.bundle}</td>
                    <td>{bundle.markets}</td>
                    <td>{bundle.strategies}</td>
                    <td align="right">{bundle.summary.avg_fill_rate.toFixed(3)}</td>
                    <td align="right">{bundle.summary.avg_reject_rate.toFixed(3)}</td>
                    <td align="right">{bundle.summary.avg_quality_score.toFixed(3)}</td>
                    <td>
                      <span className={`status-chip status-chip-${label}`}>{label}</span>
                    </td>
                    <td>
                      <div style={{ display: "grid", gap: 2 }}>
                        <code>{bundle.report_path}</code>
                        <code>{bundle.leaderboard_path}</code>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </article>
    </section>
  );
}
