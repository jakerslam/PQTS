import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { webEnv } from "@/lib/env";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session";

interface ProxyOptions {
  method?: "GET" | "POST";
  body?: unknown;
}

function upstreamUrl(path: string): string {
  const base = webEnv.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}

export async function proxyApi(path: string, options: ProxyOptions = {}): Promise<NextResponse> {
  const method = options.method ?? "GET";
  const jar = await cookies();
  const sessionToken = jar.get(SESSION_COOKIE_NAME)?.value;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${webEnv.NEXT_PUBLIC_API_TOKEN}`,
    Accept: "application/json",
  };
  if (sessionToken) {
    headers["X-Session-Token"] = sessionToken;
  }
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  try {
    const response = await fetch(upstreamUrl(path), {
      method,
      cache: "no-store",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
    const text = await response.text();
    const contentType = response.headers.get("content-type") ?? "application/json";
    return new NextResponse(text || "{}", {
      status: response.status,
      headers: { "Content-Type": contentType },
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "upstream_unreachable",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }
}
