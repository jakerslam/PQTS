import { NextResponse } from "next/server";

import { runPython } from "@/lib/ops/exec";

interface SeedBody {
  venue?: "binance" | "coinbase" | "all";
  interval?: string;
  start?: string;
  end?: string;
  format?: "csv" | "parquet";
  cache_mode?: "use" | "refresh";
  max_retries?: number;
  execute?: boolean;
}

function buildSeedCommand(payload: SeedBody): string[] {
  const venue = payload.venue ?? "all";
  const interval = payload.interval ?? "1h";
  const start = payload.start ?? "2026-01-01";
  const end = payload.end ?? "2026-03-01";
  const format = payload.format ?? "csv";
  const cacheMode = payload.cache_mode ?? "use";
  const maxRetries = Number(payload.max_retries ?? 3);
  return [
    "scripts/download_historical_data.py",
    "--venue",
    venue,
    "--interval",
    interval,
    "--start",
    start,
    "--end",
    end,
    "--format",
    format,
    "--cache-mode",
    cacheMode,
    "--max-retries",
    String(Number.isFinite(maxRetries) ? Math.max(1, maxRetries) : 3),
  ];
}

export async function GET() {
  return NextResponse.json({
    presets: [
      {
        label: "Crypto 1h (Q1 sample)",
        venue: "binance",
        interval: "1h",
        start: "2026-01-01",
        end: "2026-03-01",
      },
      {
        label: "Cross-venue 1h (Q1 sample)",
        venue: "all",
        interval: "1h",
        start: "2026-01-01",
        end: "2026-03-01",
      },
    ],
  });
}

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => ({}))) as SeedBody;
  const command = buildSeedCommand(payload);
  if (!payload.execute) {
    return NextResponse.json({
      dry_run: true,
      command: ["python3", ...command],
      note: "Set execute=true to run bounded data bootstrap with cache/checksum/retry controls.",
    });
  }
  const result = await runPython(command, { timeoutMs: 180_000 });
  return NextResponse.json({
    dry_run: false,
    ...result,
    output_lines: result.stdout.split(/\r?\n/).filter((line) => line.trim().length > 0),
  });
}
