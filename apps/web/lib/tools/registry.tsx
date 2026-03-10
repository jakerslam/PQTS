import React from "react";
import { AccountSummaryToolCard } from "@/components/tool-renderers/account-summary-card";
import { OrdersTapeToolCard } from "@/components/tool-renderers/orders-tape-card";
import { RiskStateToolCard } from "@/components/tool-renderers/risk-state-card";
import { ToolFallbackCard } from "@/components/tool-renderers/fallback-card";
import { ToolLoadingCard } from "@/components/tool-renderers/loading-card";
import type { ToolLifecycleEvent, ToolRendererRegistration } from "@/lib/tools/types";

const toolRegistry: Record<string, ToolRendererRegistration> = {
  account_summary: {
    toolType: "account_summary",
    LoadingComponent: ToolLoadingCard,
    FinalComponent: AccountSummaryToolCard,
  },
  orders_tape: {
    toolType: "orders_tape",
    LoadingComponent: ToolLoadingCard,
    FinalComponent: OrdersTapeToolCard,
  },
  risk_state: {
    toolType: "risk_state",
    LoadingComponent: ToolLoadingCard,
    FinalComponent: RiskStateToolCard,
  },
};

export function getRegisteredToolTypes(): string[] {
  return Object.keys(toolRegistry).sort();
}

export function resolveToolRegistration(toolType: string): ToolRendererRegistration | null {
  return toolRegistry[toolType] ?? null;
}

export function renderToolEvent(event: ToolLifecycleEvent): React.ReactElement {
  const registration = resolveToolRegistration(event.toolType);
  if (!registration) {
    return <ToolFallbackCard event={event} />;
  }
  if (event.status === "loading") {
    const Loading = registration.LoadingComponent;
    return <Loading event={event} />;
  }
  const Final = registration.FinalComponent;
  return <Final event={event} />;
}
