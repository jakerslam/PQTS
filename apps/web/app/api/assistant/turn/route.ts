import { NextResponse } from "next/server";

import { proxyApi } from "@/lib/api/server-proxy";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as { message?: string };
  const message = String(body.message ?? "").trim();
  if (!message) {
    return NextResponse.json({ error: "message is required" }, { status: 400 });
  }
  return proxyApi("/v1/assistant/turn", {
    method: "POST",
    body: { message },
  });
}
