export async function GET() {
  return new Response(
    JSON.stringify({
      error: "deprecated_endpoint",
      detail: "Use /api/onboarding/runs/{runId} polling against canonical API state.",
    }),
    {
      status: 410,
      headers: { "Content-Type": "application/json" },
    },
  );
}
