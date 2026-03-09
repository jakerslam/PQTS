import type { ToolLifecycleEvent } from "@/lib/tools/types";

export type AssistantStreamEvent =
  | { eventId: string; kind: "token"; value: string }
  | { eventId: string; kind: "tool_started"; toolType: string; toolCallId: string }
  | {
      eventId: string;
      kind: "tool_update";
      toolCallId: string;
      payload: unknown;
      status?: "loading" | "complete" | "error";
      errorMessage?: string;
    }
  | { eventId: string; kind: "tool_completed"; toolCallId: string; payload: unknown }
  | { eventId: string; kind: "tool_failed"; toolCallId: string; errorMessage: string }
  | { eventId: string; kind: "turn_completed" }
  | { eventId: string; kind: "turn_failed"; errorMessage: string };

export interface AssistantTurnState {
  turnId: string;
  text: string;
  isComplete: boolean;
  errorMessage?: string;
  toolEvents: Record<string, ToolLifecycleEvent>;
  orderedToolCallIds: string[];
  processedEventIds: string[];
}
