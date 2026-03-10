import { NextResponse } from "next/server";

import { buildOnboardingPlan } from "@/lib/onboarding/plan";
import { startOnboardingRun } from "@/lib/onboarding/run-store";

interface Body {
  experience?: "beginner" | "intermediate" | "advanced";
  automation?: "manual" | "assisted" | "auto";
  capitalUsd?: number;
}

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => ({}))) as Body;
  const plan = buildOnboardingPlan({
    experience: payload.experience ?? "beginner",
    automation: payload.automation ?? "manual",
    capitalUsd: Number(payload.capitalUsd ?? 5000),
  });
  const run = startOnboardingRun(plan.commands);
  return NextResponse.json({
    run,
    plan,
  });
}
