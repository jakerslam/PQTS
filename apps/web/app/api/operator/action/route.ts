import { NextResponse } from "next/server";

import { recordOperatorAction } from "@/lib/operator/actions";

interface Body {
  kind?:
    | "pause_trading"
    | "resume_trading"
    | "canary_promote"
    | "canary_hold"
    | "ack_incident";
  actor?: string;
  note?: string;
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as Body;
  const kind = body.kind;
  const actor = (body.actor ?? "operator").trim();
  const note = (body.note ?? "").trim();

  if (!kind) {
    return NextResponse.json({ error: "kind is required" }, { status: 400 });
  }

  const action = recordOperatorAction({ kind, actor, note });
  return NextResponse.json({ action });
}
