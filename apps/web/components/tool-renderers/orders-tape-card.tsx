import React from "react";
import type { ToolRendererProps } from "@/lib/tools/types";

export function OrdersTapeToolCard({ event }: ToolRendererProps) {
  const payload = (event.payload ?? {}) as { rows?: Array<Record<string, unknown>> };
  const rows = Array.isArray(payload.rows) ? payload.rows : [];
  return (
    <article className="card">
      <h3 style={{ marginTop: 0 }}>Orders Tape</h3>
      <p>Rows: {rows.length}</p>
      <p style={{ marginBottom: 0, color: "var(--muted)" }}>
        Tool registry matched this event to the orders-tape renderer.
      </p>
    </article>
  );
}
