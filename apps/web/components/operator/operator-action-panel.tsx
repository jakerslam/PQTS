"use client";

import { useEffect, useState } from "react";

import type { OperatorActionKind, OperatorActionRecord } from "@/lib/operator/actions";

interface ActionResponse {
  actions: OperatorActionRecord[];
}

async function fetchActions(): Promise<OperatorActionRecord[]> {
  const response = await fetch("/api/operator/actions", { cache: "no-store" });
  if (!response.ok) {
    return [];
  }
  const payload = (await response.json()) as ActionResponse;
  return Array.isArray(payload.actions) ? payload.actions : [];
}

export function OperatorActionPanel() {
  const [actions, setActions] = useState<OperatorActionRecord[]>([]);
  const [note, setNote] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  async function refresh() {
    setActions(await fetchActions());
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function submitAction(kind: OperatorActionKind) {
    if (isBusy) return;
    setIsBusy(true);
    try {
      await fetch("/api/operator/action", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ kind, actor: "operator", note: note.trim() }),
      });
      setNote("");
      await refresh();
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="card" style={{ display: "grid", gap: 10 }}>
      <h3 style={{ margin: 0 }}>Operator Actions</h3>
      <p style={{ margin: 0, color: "var(--muted)" }}>
        Pause/resume, canary decisioning, and incident acknowledgments.
      </p>
      <textarea
        rows={2}
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder="optional note"
      />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <button type="button" disabled={isBusy} onClick={() => submitAction("pause_trading")}>
          Pause
        </button>
        <button type="button" disabled={isBusy} onClick={() => submitAction("resume_trading")}>
          Resume
        </button>
        <button type="button" disabled={isBusy} onClick={() => submitAction("canary_promote")}>
          Canary Promote
        </button>
        <button type="button" disabled={isBusy} onClick={() => submitAction("canary_hold")}>
          Canary Hold
        </button>
        <button type="button" disabled={isBusy} onClick={() => submitAction("ack_incident")}>
          Acknowledge Incident
        </button>
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        {actions.length === 0 ? (
          <p style={{ margin: 0, color: "var(--muted)" }}>No operator actions recorded yet.</p>
        ) : (
          actions.map((row) => (
            <article key={row.id} className="card" style={{ padding: 8 }}>
              <p style={{ margin: 0 }}>
                <strong>{row.kind}</strong> · {row.actor}
              </p>
              <p style={{ margin: "4px 0 0", color: "var(--muted)" }}>
                {row.note || "(no note)"} · {row.createdAt}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
