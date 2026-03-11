import { getReplay } from "@/lib/api/client";

export default async function ReplayPage() {
  const replay = await getReplay(240).catch(() => ({
    hash: "",
    count: 0,
    event_types: [],
    events: [],
  }));
  const events = replay.events;
  const counts = replay.event_types;
  const hash = replay.hash || "unknown";

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <article className="card">
        <h2 style={{ marginTop: 0 }}>Deterministic Replay Timeline</h2>
        <p style={{ margin: "0 0 8px", color: "var(--muted)" }}>
          Replay hash: <code>{hash}</code>
        </p>
        <p style={{ margin: 0, color: "var(--muted)" }}>
          Events loaded: {replay.count}
        </p>
      </article>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Event Type Distribution</h3>
        {counts.length === 0 ? (
          <p style={{ margin: 0, color: "var(--muted)" }}>No replay events found in latest reference bundle.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Event Type</th>
                <th align="right">Count</th>
              </tr>
            </thead>
            <tbody>
              {counts.map((row) => (
                <tr key={row.event_type}>
                  <td>{row.event_type}</td>
                  <td align="right">{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>

      <article className="card">
        <h3 style={{ marginTop: 0 }}>Timeline</h3>
        {events.length === 0 ? (
          <p style={{ margin: 0, color: "var(--muted)" }}>No timeline entries available.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Cycle</th>
                <th align="left">Event</th>
                <th align="left">Market</th>
                <th align="left">Strategy</th>
                <th align="left">Run ID</th>
              </tr>
            </thead>
            <tbody>
              {events.slice(0, 150).map((event, index) => (
                <tr key={`${String(event.event_id ?? index)}:${index}`}>
                  <td>{String(event.cycle ?? "-")}</td>
                  <td>{String(event.event_type ?? "unknown")}</td>
                  <td>{String(event.market ?? "-")}</td>
                  <td>{String(event.strategy ?? "-")}</td>
                  <td>{String(event.run_id ?? "-")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>
    </section>
  );
}
