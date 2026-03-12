import { webEnv } from "@/lib/env";
import type {
  AccountSummary,
  AssistantAuditEvent,
  BrokerageAccount,
  BrokerageSyncHealthRow,
  ExecutionQualityRow,
  Fill,
  Order,
  OrderTruthPayload,
  Position,
  ReplayPayload,
  ReferencePerformance,
  RiskState,
  TerminalPayload,
  TerminalProfile,
} from "@/lib/api/types";

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${webEnv.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: {
      Authorization: `Bearer ${webEnv.NEXT_PUBLIC_API_TOKEN}`,
      Accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`API request failed (${response.status}): ${path}`);
  }
  return (await response.json()) as T;
}

interface AccountEnvelope {
  account: {
    account_id: string;
    equity: number;
    cash: number;
    buying_power: number;
  };
}

interface PositionEnvelope {
  positions: Array<{
    symbol: string;
    quantity: number;
    avg_price: number;
    mark_price: number;
    unrealized_pnl: number;
  }>;
}

interface OrderEnvelope {
  orders: Array<{
    order_id: string;
    symbol: string;
    side: "buy" | "sell";
    quantity: number;
    status: string;
    submitted_at: string;
  }>;
}

interface FillEnvelope {
  fills: Array<{
    fill_id: string;
    order_id: string;
    symbol: string;
    quantity: number;
    price: number;
    executed_at: string;
  }>;
}

interface RiskEnvelope {
  risk_state: {
    kill_switch_active: boolean;
    reasons: string[];
    current_drawdown: number;
    metadata?: Record<string, unknown>;
  };
}

interface ExecutionQualityEnvelope {
  rows: Array<{
    trade_id: string;
    strategy_id: string;
    symbol: string;
    exchange: string;
    side: string;
    quantity: number;
    price: number;
    realized_slippage_bps: number;
    predicted_slippage_bps: number;
    realized_net_alpha_usd: number;
    timestamp: string;
  }>;
}

interface OrderTruthEnvelope {
  selected: ExecutionQualityEnvelope["rows"][number] | null;
  rows: ExecutionQualityEnvelope["rows"];
  explanation: string[];
  evidence_bundle?: OrderTruthPayload["evidence_bundle"];
}

interface BrokerageAccountsEnvelope {
  accounts: BrokerageAccount[];
  totals: {
    accounts: number;
    total_balance_current_usd: number;
    total_balance_available_usd: number;
  };
}

interface BrokerageSyncHealthEnvelope {
  connections: BrokerageSyncHealthRow[];
  degraded_count: number;
  all_clear: boolean;
}

interface AssistantAuditEnvelope {
  events: AssistantAuditEvent[];
  count: number;
}

export async function getAccountSummary(): Promise<AccountSummary> {
  const payload = await apiGet<AccountEnvelope>(`/v1/accounts/${webEnv.NEXT_PUBLIC_ACCOUNT_ID}`);
  return payload.account;
}

export async function getPositions(): Promise<Position[]> {
  const payload = await apiGet<PositionEnvelope>(
    `/v1/portfolio/positions?account_id=${encodeURIComponent(webEnv.NEXT_PUBLIC_ACCOUNT_ID)}`,
  );
  return payload.positions.map((row) => ({
    symbol: row.symbol,
    qty: Number(row.quantity),
    avg_price: Number(row.avg_price),
    market_price: Number(row.mark_price),
    unrealized_pnl: Number(row.unrealized_pnl),
  }));
}

export async function getOrders(): Promise<Order[]> {
  const payload = await apiGet<OrderEnvelope>(
    `/v1/execution/orders?account_id=${encodeURIComponent(webEnv.NEXT_PUBLIC_ACCOUNT_ID)}`,
  );
  return payload.orders.map((row) => ({
    order_id: row.order_id,
    symbol: row.symbol,
    side: row.side,
    quantity: Number(row.quantity),
    status: row.status,
    created_at: row.submitted_at,
  }));
}

export async function getFills(): Promise<Fill[]> {
  const payload = await apiGet<FillEnvelope>(
    `/v1/execution/fills?account_id=${encodeURIComponent(webEnv.NEXT_PUBLIC_ACCOUNT_ID)}`,
  );
  return payload.fills.map((row) => ({
    fill_id: row.fill_id,
    order_id: row.order_id,
    symbol: row.symbol,
    quantity: Number(row.quantity),
    price: Number(row.price),
    timestamp: row.executed_at,
  }));
}

export async function getRiskState(): Promise<RiskState> {
  const payload = await apiGet<RiskEnvelope>(`/v1/risk/state/${webEnv.NEXT_PUBLIC_ACCOUNT_ID}`);
  return {
    kill_switch_active: Boolean(payload.risk_state.kill_switch_active),
    kill_switch_reason: String(payload.risk_state.reasons?.[0] ?? ""),
    current_drawdown: Number(payload.risk_state.current_drawdown),
    daily_pnl: Number(payload.risk_state.metadata?.daily_pnl ?? 0),
  };
}

function mapExecutionQualityRow(row: ExecutionQualityEnvelope["rows"][number]): ExecutionQualityRow {
  return {
    trade_id: String(row.trade_id),
    strategy_id: String(row.strategy_id),
    symbol: String(row.symbol),
    exchange: String(row.exchange),
    side: String(row.side),
    quantity: Number(row.quantity),
    price: Number(row.price),
    realized_slippage_bps: Number(row.realized_slippage_bps),
    predicted_slippage_bps: Number(row.predicted_slippage_bps),
    realized_net_alpha_usd: Number(row.realized_net_alpha_usd),
    timestamp: String(row.timestamp),
  };
}

export async function getReferencePerformance(): Promise<ReferencePerformance> {
  return apiGet<ReferencePerformance>(`/v1/ops/reference-performance`);
}

export async function getExecutionQuality(limit = 200): Promise<ExecutionQualityRow[]> {
  const bounded = Math.min(Math.max(Math.floor(limit), 1), 2000);
  const payload = await apiGet<ExecutionQualityEnvelope>(`/v1/ops/execution-quality?limit=${bounded}`);
  return payload.rows.map(mapExecutionQualityRow);
}

export async function getOrderTruth(orderId?: string): Promise<OrderTruthPayload> {
  const params = new URLSearchParams();
  if (orderId) {
    params.set("order_id", orderId);
  }
  const suffix = params.toString();
  const path = suffix ? `/v1/ops/order-truth?${suffix}` : "/v1/ops/order-truth";
  const payload = await apiGet<OrderTruthEnvelope>(path);
  return {
    selected: payload.selected ? mapExecutionQualityRow(payload.selected) : null,
    rows: payload.rows.map(mapExecutionQualityRow),
    explanation: Array.isArray(payload.explanation) ? payload.explanation.map((item) => String(item)) : [],
    evidence_bundle:
      payload.evidence_bundle && typeof payload.evidence_bundle === "object"
        ? payload.evidence_bundle
        : null,
  };
}

export async function getReplay(limit = 120): Promise<ReplayPayload> {
  const bounded = Math.min(Math.max(Math.floor(limit), 1), 1000);
  return apiGet<ReplayPayload>(`/v1/ops/replay?limit=${bounded}`);
}

export async function getBrokerageAccounts(): Promise<BrokerageAccountsEnvelope> {
  return apiGet<BrokerageAccountsEnvelope>(`/v1/integrations/brokerage/accounts`);
}

export async function getBrokerageSyncHealth(): Promise<BrokerageSyncHealthEnvelope> {
  return apiGet<BrokerageSyncHealthEnvelope>(`/v1/integrations/brokerage/sync-health`);
}

export async function getTerminal(): Promise<TerminalPayload> {
  return apiGet<TerminalPayload>(`/v1/studio/terminal`);
}

export async function getAssistantAudit(limit = 100): Promise<AssistantAuditEnvelope> {
  const bounded = Math.min(Math.max(Math.floor(limit), 1), 500);
  return apiGet<AssistantAuditEnvelope>(`/v1/assistant/audit?limit=${bounded}`);
}

export async function updateTerminalPreferences(profile: Partial<TerminalProfile>): Promise<TerminalProfile> {
  const response = await fetch(`${webEnv.NEXT_PUBLIC_API_BASE_URL}/v1/studio/terminal/preferences`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${webEnv.NEXT_PUBLIC_API_TOKEN}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(profile),
  });
  if (!response.ok) {
    throw new Error(`API request failed (${response.status}): /v1/studio/terminal/preferences`);
  }
  const payload = (await response.json()) as { profile: TerminalProfile };
  return payload.profile;
}
