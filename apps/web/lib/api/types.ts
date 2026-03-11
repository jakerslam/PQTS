export interface AccountSummary {
  account_id: string;
  equity: number;
  cash: number;
  buying_power: number;
}

export interface Position {
  symbol: string;
  qty: number;
  avg_price: number;
  market_price: number;
  unrealized_pnl: number;
}

export interface Order {
  order_id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  status: string;
  created_at: string;
}

export interface Fill {
  fill_id: string;
  order_id: string;
  symbol: string;
  quantity: number;
  price: number;
  timestamp: string;
}

export interface RiskState {
  kill_switch_active: boolean;
  kill_switch_reason: string;
  current_drawdown: number;
  daily_pnl: number;
}

export interface ReferenceBundleSummary {
  bundle: string;
  path: string;
  report_path: string;
  leaderboard_path: string;
  markets: string;
  strategies: string;
  summary: {
    avg_fill_rate: number;
    avg_quality_score: number;
    avg_reject_rate: number;
    total_filled: number;
    total_rejected: number;
    total_submitted: number;
  };
}

export interface ReferenceProvenance {
  trust_label: "reference" | "diagnostic_only" | "unverified";
  generated_at: string;
  bundle: string;
  report_path: string;
  leaderboard_path: string;
  source_path: string;
}

export interface ReferencePerformance {
  generated_at: string;
  bundle_count: number;
  bundles: ReferenceBundleSummary[];
  provenance?: ReferenceProvenance;
}

export interface ExecutionQualityRow {
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
}

export interface OrderTruthPayload {
  selected: ExecutionQualityRow | null;
  rows: ExecutionQualityRow[];
  explanation: string[];
  evidence_bundle?: {
    candidate_id: string;
    strategy_id: string;
    trust_label: string;
    quote_ts: string;
    decision_ts: string;
    order_submit_ts: string;
    latency_ms: number;
    source_count: number;
    skew_seconds: number;
    causal_ok: boolean;
    event_minus_quote_seconds: number;
    risk_gate_decision: string;
    risk_gate_reason_codes: string[];
    expected_net_ev: number;
  } | null;
}

export interface ReplayEventTypeCount {
  event_type: string;
  count: number;
}

export interface ReplayPayload {
  hash: string;
  count: number;
  event_types: ReplayEventTypeCount[];
  events: Array<Record<string, unknown>>;
}
