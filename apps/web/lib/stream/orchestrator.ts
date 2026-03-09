import type { AssistantStreamEvent, AssistantTurnState } from "@/lib/stream/types";
import type { ToolLifecycleEvent } from "@/lib/tools/types";

export function createAssistantTurnState(turnId: string): AssistantTurnState {
  return {
    turnId,
    text: "",
    isComplete: false,
    toolEvents: {},
    orderedToolCallIds: [],
    processedEventIds: [],
  };
}

function cloneToolEvent(toolType: string, current?: ToolLifecycleEvent): ToolLifecycleEvent {
  return {
    toolType,
    status: current?.status ?? "loading",
    payload: current?.payload,
    startedAt: current?.startedAt,
    endedAt: current?.endedAt,
    errorMessage: current?.errorMessage,
  };
}

export function applyAssistantStreamEvent(
  current: AssistantTurnState,
  event: AssistantStreamEvent,
): AssistantTurnState {
  if (current.processedEventIds.includes(event.eventId)) {
    return current;
  }

  const next: AssistantTurnState = {
    ...current,
    toolEvents: { ...current.toolEvents },
    orderedToolCallIds: [...current.orderedToolCallIds],
    processedEventIds: [...current.processedEventIds, event.eventId],
  };

  switch (event.kind) {
    case "token": {
      next.text = `${next.text}${event.value}`;
      return next;
    }
    case "tool_started": {
      if (!next.orderedToolCallIds.includes(event.toolCallId)) {
        next.orderedToolCallIds.push(event.toolCallId);
      }
      next.toolEvents[event.toolCallId] = {
        toolType: event.toolType,
        status: "loading",
      };
      return next;
    }
    case "tool_update": {
      const currentTool = next.toolEvents[event.toolCallId];
      const tool = cloneToolEvent(currentTool?.toolType ?? "unknown_tool", currentTool);
      tool.payload = event.payload;
      if (event.status) {
        tool.status = event.status;
      }
      if (event.errorMessage) {
        tool.errorMessage = event.errorMessage;
      }
      next.toolEvents[event.toolCallId] = tool;
      if (!next.orderedToolCallIds.includes(event.toolCallId)) {
        next.orderedToolCallIds.push(event.toolCallId);
      }
      return next;
    }
    case "tool_completed": {
      const currentTool = next.toolEvents[event.toolCallId];
      const tool = cloneToolEvent(currentTool?.toolType ?? "unknown_tool", currentTool);
      tool.payload = event.payload;
      tool.status = "complete";
      next.toolEvents[event.toolCallId] = tool;
      if (!next.orderedToolCallIds.includes(event.toolCallId)) {
        next.orderedToolCallIds.push(event.toolCallId);
      }
      return next;
    }
    case "tool_failed": {
      const currentTool = next.toolEvents[event.toolCallId];
      const tool = cloneToolEvent(currentTool?.toolType ?? "unknown_tool", currentTool);
      tool.status = "error";
      tool.errorMessage = event.errorMessage;
      next.toolEvents[event.toolCallId] = tool;
      if (!next.orderedToolCallIds.includes(event.toolCallId)) {
        next.orderedToolCallIds.push(event.toolCallId);
      }
      return next;
    }
    case "turn_completed": {
      next.isComplete = true;
      return next;
    }
    case "turn_failed": {
      next.isComplete = true;
      next.errorMessage = event.errorMessage;
      return next;
    }
    default:
      return next;
  }
}

export function reduceAssistantStream(
  turnId: string,
  events: AssistantStreamEvent[],
): AssistantTurnState {
  return events.reduce(applyAssistantStreamEvent, createAssistantTurnState(turnId));
}
