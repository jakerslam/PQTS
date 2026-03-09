import { reduceAssistantStream } from "@/lib/stream/orchestrator";
import type { AssistantStreamEvent } from "@/lib/stream/types";
import { ToolEventRenderer } from "@/components/tool-renderers/tool-event-renderer";

const SAMPLE_EVENTS: AssistantStreamEvent[] = [
  { eventId: "1", kind: "token", value: "Generating execution summary... " },
  { eventId: "2", kind: "tool_started", toolType: "risk_state", toolCallId: "tool_1" },
  {
    eventId: "3",
    kind: "tool_completed",
    toolCallId: "tool_1",
    payload: { kill_switch_active: false, kill_switch_reason: "" },
  },
  { eventId: "4", kind: "token", value: "done." },
  { eventId: "5", kind: "turn_completed" },
];

export function StreamTurnPreview() {
  const state = reduceAssistantStream("demo_turn", SAMPLE_EVENTS);

  return (
    <section className="card">
      <h3 style={{ marginTop: 0 }}>Stream Orchestrator Preview</h3>
      <p>
        <strong>Assistant text:</strong> {state.text}
      </p>
      <p>
        <strong>Complete:</strong> {state.isComplete ? "yes" : "no"}
      </p>
      {state.orderedToolCallIds.map((callId) => {
        const event = state.toolEvents[callId];
        return event ? <ToolEventRenderer key={callId} event={event} /> : null;
      })}
    </section>
  );
}
