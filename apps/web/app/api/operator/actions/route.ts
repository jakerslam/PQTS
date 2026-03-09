import { NextResponse } from "next/server";

import { listOperatorActions } from "@/lib/operator/actions";

export async function GET() {
  return NextResponse.json({ actions: listOperatorActions(100) });
}
