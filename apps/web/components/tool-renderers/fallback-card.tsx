import type { ToolRendererProps } from "@/lib/tools/types";

export function ToolFallbackCard({ event }: ToolRendererProps) {
  return (
    <article className="card">
      <h3 style={{ marginTop: 0 }}>Unsupported tool type</h3>
      <p>Type: {event.toolType || "unknown"}</p>
      <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{JSON.stringify(event.payload ?? {}, null, 2)}</pre>
    </article>
  );
}
