export type PromotionStage = "backtest" | "paper" | "shadow" | "canary" | "live" | "halted";
export type PromotionAction = "advance" | "hold" | "rollback" | "halt";

export interface PromotionRecord {
  strategy_id: string;
  stage: PromotionStage;
  capital_allocation_pct: number;
  rollback_trigger: string;
  updated_at: string;
  history: Array<{
    action: PromotionAction;
    actor: string;
    note: string;
    from_stage: PromotionStage;
    to_stage: PromotionStage;
    at: string;
  }>;
}

const STAGE_ORDER: PromotionStage[] = ["backtest", "paper", "shadow", "canary", "live"];

const promotionStore = new Map<string, PromotionRecord>();

function nowIso(): string {
  return new Date().toISOString();
}

function stageForAction(stage: PromotionStage, action: PromotionAction): PromotionStage {
  if (action === "hold") {
    return stage;
  }
  if (action === "halt") {
    return "halted";
  }
  if (action === "rollback") {
    const idx = STAGE_ORDER.indexOf(stage);
    if (idx <= 0) {
      return "backtest";
    }
    return STAGE_ORDER[idx - 1];
  }
  const idx = STAGE_ORDER.indexOf(stage);
  if (idx < 0 || idx >= STAGE_ORDER.length - 1) {
    return stage;
  }
  return STAGE_ORDER[idx + 1];
}

function defaultRecord(strategyId: string): PromotionRecord {
  return {
    strategy_id: strategyId,
    stage: "paper",
    capital_allocation_pct: 2,
    rollback_trigger: "reject_rate>0.30 or slippage_mape_pct>25",
    updated_at: nowIso(),
    history: [],
  };
}

export function listPromotionRecords(): PromotionRecord[] {
  if (promotionStore.size === 0) {
    for (const strategy of ["trend_following", "funding_arbitrage", "market_making"]) {
      promotionStore.set(strategy, defaultRecord(strategy));
    }
  }
  return [...promotionStore.values()].sort((left, right) => left.strategy_id.localeCompare(right.strategy_id));
}

export function applyPromotionAction(params: {
  strategy_id: string;
  action: PromotionAction;
  actor: string;
  note?: string;
}): PromotionRecord {
  const strategyId = params.strategy_id.trim() || "unknown";
  const current = promotionStore.get(strategyId) ?? defaultRecord(strategyId);
  const nextStage = stageForAction(current.stage, params.action);
  const updated: PromotionRecord = {
    ...current,
    stage: nextStage,
    updated_at: nowIso(),
    history: [
      {
        action: params.action,
        actor: params.actor.trim() || "operator",
        note: params.note?.trim() ?? "",
        from_stage: current.stage,
        to_stage: nextStage,
        at: nowIso(),
      },
      ...current.history,
    ].slice(0, 100),
  };
  promotionStore.set(strategyId, updated);
  return updated;
}
