import React from "react";
import type { ToolRendererProps } from "@/lib/tools/types";

export function ToolLoadingCard({ event }: ToolRendererProps) {
  return (
    <article className="card">
      <h3 style={{ marginTop: 0 }}>Running tool: {event.toolType}</h3>
      <p style={{ color: "var(--muted)", marginBottom: 0 }}>Streaming tool execution...</p>
    </article>
  );
}
