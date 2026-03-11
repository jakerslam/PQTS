import { proxyApi } from "@/lib/api/server-proxy";

interface Body {
  experience?: "beginner" | "intermediate" | "advanced";
  automation?: "manual" | "assisted" | "auto";
  capitalUsd?: number;
}

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => ({}))) as Body;
  return proxyApi("/v1/onboarding/runs", {
    method: "POST",
    body: {
      experience: payload.experience ?? "beginner",
      automation: payload.automation ?? "manual",
      capital_usd: Number(payload.capitalUsd ?? 5000),
    },
  });
}
