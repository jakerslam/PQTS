import { renderToolEvent } from "@/lib/tools/registry";
import type { ToolLifecycleEvent } from "@/lib/tools/types";

export function ToolEventRenderer({ event }: { event: ToolLifecycleEvent }) {
  return renderToolEvent(event);
}
