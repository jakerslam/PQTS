import { proxyApi } from "@/lib/api/server-proxy";

export const runtime = "nodejs";

export async function GET() {
  return proxyApi("/v1/auth/me");
}
