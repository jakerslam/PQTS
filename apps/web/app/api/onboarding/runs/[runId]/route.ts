import { proxyApi } from "@/lib/api/server-proxy";

interface Params {
  params: Promise<{
    runId: string;
  }>;
}

export async function GET(_request: Request, context: Params) {
  const { runId } = await context.params;
  return proxyApi(`/v1/onboarding/runs/${encodeURIComponent(runId)}`);
}
