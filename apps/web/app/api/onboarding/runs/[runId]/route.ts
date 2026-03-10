import { NextResponse } from "next/server";

import { getOnboardingRun } from "@/lib/onboarding/run-store";

interface Params {
  params: Promise<{
    runId: string;
  }>;
}

export async function GET(_request: Request, context: Params) {
  const { runId } = await context.params;
  const run = getOnboardingRun(runId);
  if (!run) {
    return NextResponse.json({ error: "run not found" }, { status: 404 });
  }
  return NextResponse.json({ run });
}
