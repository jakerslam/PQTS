import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import { loadBestReferenceBundle, loadReferencePerformance } from "@/lib/ops/reference-data";
import { resolveRepoRoot } from "@/lib/ops/repo-root";

export type UiDensityMode = "guided" | "pro";

export interface TrustStatusSnapshot {
  environment: "demo" | "paper" | "shadow" | "canary" | "live";
  workspace: string;
  accountId: string;
  venue: string;
  dataFreshnessSeconds: number;
  nativeHotpath: "native" | "fallback";
  killSwitchState: "active" | "normal" | "unknown";
  trustLabel: "reference" | "diagnostic_only" | "unverified";
  traceId: string;
  runId: string;
  generatedAt: string;
}

function inferEnvironment(): TrustStatusSnapshot["environment"] {
  const token = String(process.env.PQTS_STAGE ?? process.env.PQTS_ENV ?? "paper")
    .trim()
    .toLowerCase();
  if (token === "demo") return "demo";
  if (token === "shadow") return "shadow";
  if (token === "canary") return "canary";
  if (token === "live" || token === "production") return "live";
  return "paper";
}

function inferNativeHotpath(): "native" | "fallback" {
  const repoRoot = resolveRepoRoot();
  const nativeReadme = path.join(repoRoot, "results", "native_benchmarks", "README.md");
  if (fs.existsSync(nativeReadme)) {
    return "native";
  }
  return "fallback";
}

function inferTrustLabel(): TrustStatusSnapshot["trustLabel"] {
  const best = loadBestReferenceBundle();
  if (!best) {
    return "unverified";
  }
  if (best.summary.avg_quality_score >= 0.25 && best.summary.avg_fill_rate > 0.0) {
    return "reference";
  }
  if (best.summary.avg_fill_rate > 0.0) {
    return "diagnostic_only";
  }
  return "unverified";
}

function inferDataFreshnessSeconds(): number {
  const payload = loadReferencePerformance();
  const generated = String(payload.generated_at ?? "").trim();
  if (!generated) {
    return -1;
  }
  const ts = Date.parse(generated);
  if (!Number.isFinite(ts)) {
    return -1;
  }
  return Math.max(Math.floor((Date.now() - ts) / 1000), 0);
}

function token(prefix: string): string {
  const seed = `${prefix}:${Date.now()}:${Math.random().toString(36).slice(2, 10)}`;
  const digest = crypto.createHash("sha256").update(seed).digest("hex").slice(0, 16);
  return `${prefix}_${digest}`;
}

export function buildTrustStatusSnapshot(): TrustStatusSnapshot {
  const best = loadBestReferenceBundle();
  const venueHint = String(best?.markets ?? "sim")
    .split(",")[0]
    .trim();
  return {
    environment: inferEnvironment(),
    workspace: "studio-web",
    accountId: String(process.env.PQTS_ACCOUNT_ID ?? "paper-main"),
    venue: venueHint || "sim",
    dataFreshnessSeconds: inferDataFreshnessSeconds(),
    nativeHotpath: inferNativeHotpath(),
    killSwitchState: "unknown",
    trustLabel: inferTrustLabel(),
    traceId: token("trc"),
    runId: token("run"),
    generatedAt: new Date().toISOString(),
  };
}
