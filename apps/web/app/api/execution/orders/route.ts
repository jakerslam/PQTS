import { NextResponse } from "next/server";

import { webEnv } from "@/lib/env";
import { proxyApi } from "@/lib/api/server-proxy";

export const runtime = "nodejs";

type Side = "buy" | "sell";
type OrderType = "market" | "limit";
type TimeInForce = "day" | "gtc" | "ioc" | "fok";

interface CreateOrderBody {
  account_id?: string;
  symbol?: string;
  side?: Side;
  order_type?: OrderType;
  quantity?: number;
  limit_price?: number | null;
  time_in_force?: TimeInForce;
  note?: string;
}

function nowIso(): string {
  return new Date().toISOString();
}

function buildOrderId(): string {
  return `web_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const accountId =
    String(url.searchParams.get("account_id") ?? "").trim() || webEnv.NEXT_PUBLIC_ACCOUNT_ID;
  return proxyApi(`/v1/execution/orders?account_id=${encodeURIComponent(accountId)}`);
}

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => ({}))) as CreateOrderBody;

  const symbol = String(payload.symbol ?? "")
    .trim()
    .toUpperCase();
  if (!symbol) {
    return NextResponse.json({ error: "symbol is required" }, { status: 400 });
  }

  const side = payload.side === "sell" ? "sell" : payload.side === "buy" ? "buy" : "";
  if (!side) {
    return NextResponse.json({ error: "side must be buy or sell" }, { status: 400 });
  }

  const orderType = payload.order_type === "limit" ? "limit" : payload.order_type === "market" ? "market" : "";
  if (!orderType) {
    return NextResponse.json({ error: "order_type must be market or limit" }, { status: 400 });
  }

  const quantity = Number(payload.quantity ?? 0);
  if (!Number.isFinite(quantity) || quantity <= 0) {
    return NextResponse.json({ error: "quantity must be > 0" }, { status: 400 });
  }

  const limitPriceRaw = payload.limit_price;
  const limitPrice =
    limitPriceRaw === null || limitPriceRaw === undefined || Number(limitPriceRaw) === 0
      ? null
      : Number(limitPriceRaw);
  if (orderType === "limit" && (!Number.isFinite(limitPrice ?? NaN) || (limitPrice ?? 0) <= 0)) {
    return NextResponse.json({ error: "limit_price must be set for limit orders" }, { status: 400 });
  }

  const tif: TimeInForce = ["day", "gtc", "ioc", "fok"].includes(String(payload.time_in_force))
    ? (payload.time_in_force as TimeInForce)
    : "day";

  const accountId = String(payload.account_id ?? "").trim() || webEnv.NEXT_PUBLIC_ACCOUNT_ID;
  const submittedAt = nowIso();

  return proxyApi("/v1/execution/orders", {
    method: "POST",
    body: {
      order_id: buildOrderId(),
      account_id: accountId,
      symbol,
      side,
      order_type: orderType,
      status: "pending",
      quantity,
      filled_quantity: 0,
      remaining_quantity: quantity,
      submitted_at: submittedAt,
      updated_at: submittedAt,
      limit_price: orderType === "limit" ? limitPrice : null,
      stop_price: null,
      time_in_force: tif,
      metadata: {
        source: "web_trade_ticket",
        note: String(payload.note ?? "").trim(),
        paper_only: true,
      },
    },
  });
}
