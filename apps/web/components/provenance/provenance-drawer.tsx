"use client";

import { useMemo } from "react";

import type { ReferenceProvenance } from "@/lib/api/types";

interface Props {
  provenance: ReferenceProvenance;
  title?: string;
}

export function ProvenanceDrawer({ provenance, title = "Artifact provenance" }: Props) {
  const generatedAt = useMemo(() => {
    const raw = String(provenance.generated_at ?? "").trim();
    if (!raw) {
      return "unknown";
    }
    const parsed = Date.parse(raw);
    if (!Number.isFinite(parsed)) {
      return raw;
    }
    return new Date(parsed).toLocaleString();
  }, [provenance.generated_at]);

  return (
    <details className="provenance-drawer">
      <summary>{title}</summary>
      <dl className="provenance-grid">
        <dt>Trust</dt>
        <dd>
          <span className={`status-chip status-chip-${provenance.trust_label}`}>{provenance.trust_label}</span>
        </dd>
        <dt>Generated</dt>
        <dd>{generatedAt}</dd>
        <dt>Bundle</dt>
        <dd>{provenance.bundle || "unknown"}</dd>
        <dt>Source</dt>
        <dd>
          <code>{provenance.source_path || "unknown"}</code>
        </dd>
        <dt>Report</dt>
        <dd>
          <code>{provenance.report_path || "unknown"}</code>
        </dd>
        <dt>Leaderboard</dt>
        <dd>
          <code>{provenance.leaderboard_path || "unknown"}</code>
        </dd>
      </dl>
    </details>
  );
}

