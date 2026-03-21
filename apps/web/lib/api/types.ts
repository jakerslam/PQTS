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

export interface PnLSnapshot {
  account_id: string;
  period_start: string;
  period_end: string;
  realized_pnl: number;
  unrealized_pnl: number;
  gross_pnl: number;
  net_pnl: number;
  fees: number;
  as_of: string;
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
  trust_label?: "reference" | "diagnostic_only" | "unverified";
  provenance?: {
    generated_at?: string;
    generator?: string;
    dataset_manifest_path?: string;
    config_snapshot_path?: string;
    metrics_chart_path?: string;
  };
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
  schema_version?: string;
  generated_at: string;
  bundle_count: number;
  trust_label?: "reference" | "diagnostic_only" | "unverified";
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
  decision_card?: DecisionExplainabilityCard | null;
}

export interface DecisionExplainabilityCard {
  card_id: string;
  strategy_id: string;
  market_id: string;
  generated_at: string;
  p_market: number;
  p_model: number;
  posterior_before: number;
  posterior_after: number;
  posterior_delta: number;
  gross_edge_bps: number;
  total_penalty_bps: number;
  net_edge_bps: number;
  expected_value_bps: number;
  full_kelly_fraction: number;
  approved_fraction: number;
  stage: string;
  gate_passed: boolean;
  gate_reason_codes: string[];
  trust_label: string;
  evidence_source: string;
  evidence_ref: string;
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

export interface BrokerageAccount {
  account_id: string;
  connection_id: string;
  provider: string;
  institution: string;
  name: string;
  type: string;
  subtype: string;
  currency: string;
  balance_current: number;
  balance_available: number;
  as_of: string;
}

export interface BrokerageSyncHealthRow {
  link_id: string;
  connection_id: string;
  provider: string;
  institution: string;
  last_sync_at: string;
  status: "ok" | "stale" | "down";
  is_stale: boolean;
  stale_seconds: number | null;
  stale_after_seconds: number;
  fail_closed_trade_block: boolean;
}

export interface TerminalProfile {
  density: string;
  watchlist: string[];
  refresh_seconds: number;
  theme: string;
  updated_at?: string;
}

export interface TerminalPayload {
  subject: string;
  always_on: boolean;
  profile: TerminalProfile;
  portfolio_totals: {
    accounts: number;
    total_balance_current_usd: number;
    total_balance_available_usd: number;
  };
  sync_health: {
    degraded_count: number;
    all_clear: boolean;
  };
  next_actions: string[];
  generated_at: string;
}

export interface AssistantAuditEvent {
  id: string;
  subject: string;
  message: string;
  requested_action: string;
  capital_affecting: boolean;
  requires_confirmation: boolean;
  executed: boolean;
  timestamp: string;
  suggestion_count: number;
}

export interface ConnectorReadiness {
  paper_ok?: boolean;
  latency_budget?: Record<string, number>;
  reliability_budget?: Record<string, number>;
  incident_profile?: Record<string, unknown>;
}

export interface Connector {
  connector_id: string;
  provider: string;
  display_name?: string;
  connector_class?: string;
  market_classes?: string[];
  order_types?: string[];
  data_granularity?: string[];
  auth_modes?: string[];
  entitlements?: string[];
  status?: string;
  readiness?: ConnectorReadiness;
  fallback_options?: string[];
  surfaces?: string[];
  last_reviewed?: string;
  repo_urls?: string[];
  notes?: string;
}
