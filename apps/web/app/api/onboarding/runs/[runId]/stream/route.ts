import { getOnboardingRun } from "@/lib/onboarding/run-store";

interface Params {
  params: Promise<{
    runId: string;
  }>;
}

function sseChunk(event: string, payload: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
}

export async function GET(_request: Request, context: Params) {
  const { runId } = await context.params;
  const run = getOnboardingRun(runId);
  if (!run) {
    return new Response("run not found", { status: 404 });
  }

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(encoder.encode(sseChunk("snapshot", run)));
      const ticker = setInterval(() => {
        const current = getOnboardingRun(runId);
        if (!current) {
          controller.enqueue(encoder.encode(sseChunk("error", { message: "run missing" })));
          clearInterval(ticker);
          controller.close();
          return;
        }
        controller.enqueue(encoder.encode(sseChunk("snapshot", current)));
        controller.enqueue(encoder.encode(sseChunk("heartbeat", { at: new Date().toISOString() })));
        if (current.status === "completed" || current.status === "failed") {
          clearInterval(ticker);
          controller.close();
        }
      }, 1000);
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
