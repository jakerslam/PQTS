import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import { parseCsv } from "@/lib/ops/csv";
import { resolveRepoRoot } from "@/lib/ops/repo-root";

export interface ReferenceBundleSummary {
  bundle: string;
  path: string;
  report_path: string;
  leaderboard_path: string;
  markets: string;
  strategies: string;
  trust_label?: "reference" | "diagnostic_only" | "unverified";
  provenance?: {
    generated_at?: string;
    generated_by?: string;
    command?: string;
    source_policy?: string;
    code_version?: string;
    environment?: string;
  };
  summary: {
    avg_fill_rate: number;
    avg_quality_score: number;
    avg_reject_rate: number;
    total_filled: number;
    total_rejected: number;
    total_submitted: number;
  };
}

export interface ReferenceProvenance {
  trust_label: "reference" | "diagnostic_only" | "unverified";
  generated_at: string;
  bundle: string;
  report_path: string;
  leaderboard_path: string;
  source_path: string;
}

interface ReferencePerformancePayload {
  schema_version?: string;
  generated_at: string;
  bundle_count: number;
  trust_label?: "reference" | "diagnostic_only" | "unverified";
  provenance?: {
    generated_at?: string;
    generator?: string;
    source_policy?: string;
    artifact_path?: string;
    bundle_count?: number;
  };
  bundles: ReferenceBundleSummary[];
}

interface ReferenceBundleReportResult {
  tca_path?: string;
}

interface ReferenceBundleReport {
  results?: ReferenceBundleReportResult[];
}

function readJson<T>(filePath: string, fallback: T): T {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as T;
  } catch {
    return fallback;
  }
}

function referenceJsonPath(): string {
  return path.join(resolveRepoRoot(), "results", "reference_performance_latest.json");
}

export function loadReferencePerformance(): ReferencePerformancePayload {
  return readJson<ReferencePerformancePayload>(referenceJsonPath(), {
    generated_at: "",
    bundle_count: 0,
    bundles: [],
  });
}

export function loadBestReferenceBundle(): ReferenceBundleSummary | null {
  const payload = loadReferencePerformance();
  if (payload.bundles.length === 0) {
    return null;
  }
  return payload.bundles
    .slice()
    .sort((left, right) => {
      if (right.summary.avg_quality_score !== left.summary.avg_quality_score) {
        return right.summary.avg_quality_score - left.summary.avg_quality_score;
      }
      return right.summary.avg_fill_rate - left.summary.avg_fill_rate;
    })[0];
}

function inferTrustLabel(bundle: ReferenceBundleSummary | null): "reference" | "diagnostic_only" | "unverified" {
  if (!bundle) {
    return "unverified";
  }
  const explicit = String(bundle.trust_label ?? "").trim();
  if (explicit === "reference" || explicit === "diagnostic_only" || explicit === "unverified") {
    return explicit;
  }
  if (bundle.summary.avg_quality_score >= 0.25 && bundle.summary.avg_fill_rate > 0.0) {
    return "reference";
  }
  if (bundle.summary.avg_fill_rate > 0.0) {
    return "diagnostic_only";
  }
  return "unverified";
}

export function loadReferenceProvenance(): ReferenceProvenance {
  const payload = loadReferencePerformance();
  const best = loadBestReferenceBundle();
  const explicitPayloadTrust = String(payload.trust_label ?? "").trim();
  const payloadTrust =
    explicitPayloadTrust === "reference" || explicitPayloadTrust === "diagnostic_only" || explicitPayloadTrust === "unverified"
      ? explicitPayloadTrust
      : undefined;
  return {
    trust_label: inferTrustLabel(best) ?? payloadTrust ?? "unverified",
    generated_at: String(payload.provenance?.generated_at ?? payload.generated_at ?? ""),
    bundle: String(best?.bundle ?? ""),
    report_path: String(best?.report_path ?? ""),
    leaderboard_path: String(best?.leaderboard_path ?? ""),
    source_path: String(best?.path ?? ""),
  };
}

export interface ExecutionQualityRow {
  trade_id: string;
  strategy_id: string;
  symbol: string;
  exchange: string;
  side: string;
  quantity: number;
  price: number;
  realized_slippage_bps: number;
  predicted_slippage_bps: number;
  realized_net_alpha_usd: number;
  timestamp: string;
}

function parseNumber(value: string | undefined): number {
  const parsed = Number(value ?? "0");
  return Number.isFinite(parsed) ? parsed : 0;
}

export function loadExecutionQualityRows(limit = 500): ExecutionQualityRow[] {
  const best = loadBestReferenceBundle();
  if (!best) {
    return [];
  }
  const repoRoot = resolveRepoRoot();
  const reportPath = path.join(repoRoot, best.report_path);
  if (!fs.existsSync(reportPath)) {
    return [];
  }
  const report = readJson<ReferenceBundleReport>(reportPath, {});
  const results = Array.isArray(report.results) ? report.results : [];
  if (results.length === 0) {
    return [];
  }
  const tcaPath = String(results[0]?.tca_path ?? "").trim();
  if (!tcaPath) {
    return [];
  }
  const absoluteTca = path.join(repoRoot, tcaPath);
  if (!fs.existsSync(absoluteTca)) {
    return [];
  }
  const rows = parseCsv(fs.readFileSync(absoluteTca, "utf-8"));
  return rows.slice(0, Math.max(limit, 1)).map((row) => ({
    trade_id: row.trade_id ?? "",
    strategy_id: row.strategy_id ?? "",
    symbol: row.symbol ?? "",
    exchange: row.exchange ?? "",
    side: row.side ?? "",
    quantity: parseNumber(row.quantity),
    price: parseNumber(row.price),
    realized_slippage_bps: parseNumber(row.realized_slippage_bps),
    predicted_slippage_bps: parseNumber(row.predicted_slippage_bps),
    realized_net_alpha_usd: parseNumber(row.realized_net_alpha_usd),
    timestamp: row.timestamp ?? "",
  }));
}

export function loadReplayEvents(limit = 100): Array<Record<string, unknown>> {
  const best = loadBestReferenceBundle();
  if (!best) {
    return [];
  }
  const repoRoot = resolveRepoRoot();
  const eventsPath = path.join(repoRoot, best.path, "simulation_events.jsonl");
  if (!fs.existsSync(eventsPath)) {
    return [];
  }
  const lines = fs
    .readFileSync(eventsPath, "utf-8")
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .slice(0, Math.max(limit, 1));
  return lines.map((line) => {
    try {
      return JSON.parse(line) as Record<string, unknown>;
    } catch {
      return {};
    }
  });
}

export function replayHash(events: Array<Record<string, unknown>>): string {
  const canonical = JSON.stringify(events);
  return crypto.createHash("sha256").update(canonical).digest("hex");
}

export function buildOrderTruth(orderId?: string): {
  selected: ExecutionQualityRow | null;
  rows: ExecutionQualityRow[];
  explanation: string[];
} {
  const rows = loadExecutionQualityRows(300);
  const selected = rows.find((row) => row.trade_id === orderId) ?? rows[0] ?? null;
  const explanation =
    selected == null
      ? ["No execution rows found in latest reference bundle."]
      : [
          `Signal: ${selected.strategy_id} emitted ${selected.side} for ${selected.symbol}.`,
          `Risk: expected slippage budget ${selected.predicted_slippage_bps.toFixed(2)} bps.`,
          `Execution: realized slippage ${selected.realized_slippage_bps.toFixed(2)} bps on ${selected.exchange}.`,
          `Attribution: realized_net_alpha_usd=${selected.realized_net_alpha_usd.toFixed(4)}.`,
        ];
  return { selected, rows, explanation };
}
