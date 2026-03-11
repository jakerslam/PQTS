"use client";

import { useMemo, useState } from "react";

import { LiveStreamStatus } from "@/components/stream/live-stream-status";
import type { TrustStatusSnapshot, UiDensityMode } from "@/lib/system/trust-status";

interface Props {
  snapshot: TrustStatusSnapshot;
  densityMode: UiDensityMode;
}

function freshnessLabel(seconds: number): string {
  if (seconds < 0) {
    return "unknown";
  }
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m`;
}

export function TrustStatusBar({ snapshot, densityMode }: Props) {
  const [showIds, setShowIds] = useState(false);
  const ids = useMemo(() => `${snapshot.traceId} / ${snapshot.runId}`, [snapshot.runId, snapshot.traceId]);

  return (
    <section className="card trust-status-shell" aria-live="polite" role="status">
      <div className="trust-status-row">
        <span className="status-chip">workspace:{snapshot.workspace}</span>
        <span className="status-chip">env:{snapshot.environment}</span>
        <span className="status-chip">mode:{densityMode}</span>
        <span className="status-chip">acct:{snapshot.accountId}</span>
        <span className="status-chip">venue:{snapshot.venue}</span>
        <span className="status-chip">fresh:{freshnessLabel(snapshot.dataFreshnessSeconds)}</span>
        <span className="status-chip">hotpath:{snapshot.nativeHotpath}</span>
        <span className="status-chip">kill:{snapshot.killSwitchState}</span>
        <span className={`status-chip status-chip-${snapshot.trustLabel}`}>trust:{snapshot.trustLabel}</span>
        <LiveStreamStatus channel="risk" accountId={snapshot.accountId} />
        <LiveStreamStatus channel="orders" accountId={snapshot.accountId} />
        <LiveStreamStatus channel="fills" accountId={snapshot.accountId} />
        <button
          type="button"
          className="inline-link-button"
          aria-label="Toggle trace and run identifiers"
          onClick={() => setShowIds((current) => !current)}
        >
          {showIds ? "hide trace/run" : "show trace/run"}
        </button>
      </div>
      {showIds ? (
        <p style={{ margin: "8px 0 0", color: "var(--muted)", fontSize: "0.85rem" }}>
          {ids}
        </p>
      ) : null}
    </section>
  );
}
