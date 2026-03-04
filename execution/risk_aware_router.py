"""
Risk-Aware Smart Order Router

Production-grade order routing with enforced risk overlay.

This is the ONLY path to place orders - all orders must pass through here.
Any attempt to bypass this router will be caught by audit logging.

Integration:
    from execution.risk_aware_router import RiskAwareRouter

    router = RiskAwareRouter(
        risk_config=RiskLimits(max_daily_loss_pct=0.02),
        broker_config={'api_key': '...'}
    )

    # This is the ONLY way to place orders
    result = await router.submit_order(order_request, market_data, portfolio)

    # Result includes RiskDecision - check it
    if result.decision == RiskDecision.FLATTEN:
        # System is in emergency mode - no orders allowed
        pass
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

from analytics.paper_readiness import PaperTrackRecordEvaluator
from execution.capacity_curves import StrategyCapacityCurveModel
from execution.distributed_ops_state import DistributedOpsState, DistributedStateConfig
from execution.live_ops_controls import (
    OrderIdempotencyGuard,
    RateLimitConfig,
    RateLimitTracker,
)
from execution.order_ledger import ImmutableOrderLedger
from execution.realistic_costs import (
    Bps,
    NotionalUSD,
    OrderBook,
    OrderBookLevel,
    Price,
    Quantity,
    RealisticCostModel,
    Side,
)
from execution.reliability import ExecutionReliabilityMonitor
from execution.shorting_controls import ShortingRiskOverlay
from execution.smart_router import OrderRequest, OrderType, RouteDecision, SmartOrderRouter
from execution.tca_feedback import (
    ExecutionFill,
    TCADatabase,
    TCATradeRecord,
    weekly_calibrate_eta,
)
from risk.kill_switches import (
    RiskDecision,
    RiskLimits,
    RiskState,
    TradingEngine as RiskEngine,
)
from risk.regime_overlay import RegimeExposureOverlay

logger = logging.getLogger(__name__)


class _RouterToken:
    """
    Module-private capability token for adapter construction and order sends.

    Direct construction is blocked. Tokens are minted only by RiskAwareRouter via
    its private _create_token() factory and verified with exact type checks.
    """

    __slots__ = ("router_id", "created_at", "_proof")

    def __new__(cls, *args, **kwargs):
        raise RuntimeError(
            "RouterToken is module-private and can only be created by "
            "RiskAwareRouter._create_token()."
        )


def _mint_router_token(router_id: int) -> "_RouterToken":
    """Deprecated helper kept for backward compatibility."""
    return _create_router_token(router_id)


def _build_token_factory():
    """
    Build closure-backed token mint/verify functions.

    The proof marker is not exposed as a module global, which makes forged
    tokens created with object.__new__(_RouterToken) fail verification.
    """
    proof = object()

    def mint(router_id: int) -> "_RouterToken":
        token = object.__new__(_RouterToken)
        object.__setattr__(token, "router_id", router_id)
        object.__setattr__(token, "created_at", datetime.now(timezone.utc).isoformat())
        object.__setattr__(token, "_proof", proof)
        return token

    def verify(token: Any, *, router_id: Optional[int] = None) -> bool:
        if type(token) is not _RouterToken:
            return False
        if getattr(token, "_proof", None) is not proof:
            return False
        if router_id is not None and getattr(token, "router_id", None) != router_id:
            return False
        return True

    return mint, verify


_create_router_token, _verify_router_token = _build_token_factory()


def _is_valid_router_token(token: Any, *, router_id: Optional[int] = None) -> bool:
    """Module-private token verification used by all adapters."""
    return _verify_router_token(token, router_id=router_id)


@dataclass
class OrderResult:
    """Result of order submission attempt."""

    success: bool
    decision: RiskDecision
    risk_state: RiskState
    order_id: Optional[str]
    exchange: Optional[str]
    rejected_reason: Optional[str]
    audit_log: Dict


@dataclass
class VenueClient:
    """Adapter registry entry."""

    market: str
    venue: str
    symbols: List[str]
    adapter: Optional[Any]
    connected: bool
    is_stub: bool


class FillProvider(Protocol):
    """Execution fill source for paper/live environments."""

    async def get_fill(
        self,
        *,
        order_id: str,
        symbol: str,
        venue: str,
        side: str,
        requested_qty: float,
        reference_price: float,
        order_book: Optional[Dict[str, Any]] = None,
        queue_ahead_qty: Optional[float] = None,
    ) -> ExecutionFill: ...


class StubFillProvider:
    """Deterministic fill source used for paper-testing and unit tests."""

    async def get_fill(
        self,
        *,
        order_id: str,
        symbol: str,
        venue: str,
        side: str,
        requested_qty: float,
        reference_price: float,
        order_book: Optional[Dict[str, Any]] = None,
        queue_ahead_qty: Optional[float] = None,
    ) -> ExecutionFill:
        _ = order_book
        _ = queue_ahead_qty
        # Side-aware deterministic slippage: +2 bps for buys, -2 bps for sells.
        slippage_multiplier = 1.0002 if side == "buy" else 0.9998
        executed_price = float(reference_price) * slippage_multiplier
        return ExecutionFill(
            executed_price=executed_price,
            executed_qty=float(requested_qty),
            timestamp=datetime.now(timezone.utc),
            venue=venue,
            symbol=symbol,
        )


class RiskAwareRouter:
    """
    Unified order router with mandatory risk overlay.

    This is the production router - ALL orders must go through here.

    Flow:
    1. Pre-trade risk check (KillSwitchMonitor)
    2. Smart routing (SmartOrderRouter)
    3. Cost estimation (RealisticCostModel)
    4. Order execution (Exchange adapter)
    5. Post-trade logging (TCA)

    NO ORDERS can bypass step 1. Ever.
    """

    def __init__(
        self,
        risk_config: RiskLimits,
        broker_config: dict,
        fill_provider: Optional[FillProvider] = None,
        tca_db_path: Optional[str] = None,
    ):
        """
        Args:
            risk_config: Hard limits for kill switches
            broker_config: Broker API credentials and settings
        """
        # Risk overlay (Step 1)
        self.risk_engine = RiskEngine(risk_config)
        self.risk_limits = risk_config

        # Smart routing (Step 2)
        self.smart_router = SmartOrderRouter(broker_config)

        # Cost model (Step 3)
        self.cost_model = RealisticCostModel()

        # Broker adapter (Step 4 - would be real exchange adapter)
        self.broker_config = broker_config
        self.exchange_adapter = None  # Would initialize real adapter
        self._router_token = self._create_token()
        self.fill_provider: FillProvider = fill_provider or StubFillProvider()
        self.tca_db = TCADatabase(
            tca_db_path or broker_config.get("tca_db_path", "data/tca_records.csv")
        )
        self.order_ledger = ImmutableOrderLedger(
            broker_config.get("order_ledger_path", "data/analytics/order_ledger.jsonl")
        )
        self.eta_by_symbol_venue: Dict[Tuple[str, str], float] = {}
        self.market_venues: Dict[str, VenueClient] = {}
        self._markets_config: Dict[str, Any] = {}
        self.regime_overlay = RegimeExposureOverlay(broker_config.get("regime_overlay", {}))
        self.shorting_overlay = ShortingRiskOverlay(broker_config.get("shorting_controls", {}))
        reliability_cfg = broker_config.get("reliability", {})
        self.reliability_monitor = ExecutionReliabilityMonitor(
            latency_slo_ms=float(reliability_cfg.get("latency_slo_ms", 250.0)),
            rejection_slo=float(reliability_cfg.get("rejection_slo", 0.001)),
            failure_slo=float(reliability_cfg.get("failure_slo", 0.01)),
            cooldown_seconds=int(reliability_cfg.get("cooldown_seconds", 300)),
        )
        capacity_cfg = broker_config.get("capacity_curves", {})
        self.capacity_model = StrategyCapacityCurveModel(
            enabled=bool(capacity_cfg.get("enabled", False)),
            storage_path=str(
                capacity_cfg.get("storage_path", "data/analytics/capacity_curve_samples.jsonl")
            ),
            min_points=int(capacity_cfg.get("min_points", 8)),
            max_points_per_key=int(capacity_cfg.get("max_points_per_key", 300)),
            throttle_buffer=float(capacity_cfg.get("throttle_buffer", 0.95)),
        )
        self._default_expected_alpha_bps: Dict[str, float] = {
            str(key): float(value)
            for key, value in (
                broker_config.get("expected_alpha_bps_by_strategy", {}) or {}
            ).items()
        }
        self.require_live_client_order_id = bool(
            broker_config.get("require_live_client_order_id", True)
        )
        self.idempotency_guard = OrderIdempotencyGuard(
            ttl_seconds=float(broker_config.get("idempotency_ttl_seconds", 300.0))
        )
        distributed_cfg = broker_config.get("distributed_ops_state", {}) or {}
        self.distributed_ops_state = DistributedOpsState(
            DistributedStateConfig(
                redis_url=str(distributed_cfg.get("redis_url", "")),
                namespace=str(distributed_cfg.get("namespace", "pqts")),
                ttl_seconds=int(distributed_cfg.get("ttl_seconds", 300)),
            )
        )
        self.rate_limit_tracker = RateLimitTracker(
            self._parse_rate_limit_configs(broker_config.get("rate_limits", {}))
        )
        self._live_rate_limit_rejects = 0
        self._live_idempotency_rejects = 0
        self._rate_limit_denials: Dict[str, int] = {}
        self._last_live_order_error: Optional[str] = None
        self._last_live_order_controls: Dict[str, Any] = {}
        # Order admission gate to prevent race-condition bypass across state changes.
        self._submit_order_lock = asyncio.Lock()

        # Audit logging (Step 5)
        self.audit_log: List[Dict] = []
        self.order_count: int = 0
        self.reject_count: int = 0

        # Capital injection (not hardcoded)
        self._capital = None  # Set via set_capital()

        logger.info("RiskAwareRouter initialized")
        logger.info(f"  Daily loss limit: {risk_config.max_daily_loss_pct:.1%}")
        logger.info(f"  Max drawdown: {risk_config.max_drawdown_pct:.1%}")
        logger.info(f"  Max leverage: {risk_config.max_gross_leverage:.1f}x")

    def _resolve_expected_alpha_bps(self, order: OrderRequest) -> float:
        explicit = float(getattr(order, "expected_alpha_bps", 0.0) or 0.0)
        if explicit != 0.0:
            return explicit
        return float(self._default_expected_alpha_bps.get(str(order.strategy_id), 0.0))

    @staticmethod
    def _parse_rate_limit_configs(raw_cfg: Any) -> Dict[Tuple[str, str], RateLimitConfig]:
        configs: Dict[Tuple[str, str], RateLimitConfig] = {}
        if isinstance(raw_cfg, dict):
            for venue, venue_cfg in raw_cfg.items():
                venue_name = str(venue).strip().lower()
                if not venue_name:
                    continue
                if not isinstance(venue_cfg, dict):
                    continue
                if "limit" in venue_cfg and "window_seconds" in venue_cfg:
                    limit = int(venue_cfg.get("limit", 0))
                    window_seconds = float(venue_cfg.get("window_seconds", 0.0))
                    if limit > 0 and window_seconds > 0:
                        configs[(venue_name, "*")] = RateLimitConfig(
                            limit=limit,
                            window_seconds=window_seconds,
                        )
                    continue
                for endpoint, endpoint_cfg in venue_cfg.items():
                    if not isinstance(endpoint_cfg, dict):
                        continue
                    endpoint_name = str(endpoint).strip().lower() or "*"
                    limit = int(endpoint_cfg.get("limit", 0))
                    window_seconds = float(endpoint_cfg.get("window_seconds", 0.0))
                    if limit <= 0 or window_seconds <= 0:
                        continue
                    configs[(venue_name, endpoint_name)] = RateLimitConfig(
                        limit=limit,
                        window_seconds=window_seconds,
                    )
            return configs

        if isinstance(raw_cfg, list):
            for row in raw_cfg:
                if not isinstance(row, dict):
                    continue
                venue_name = str(row.get("venue", "")).strip().lower()
                if not venue_name:
                    continue
                endpoint_name = str(row.get("endpoint", "*")).strip().lower() or "*"
                limit = int(row.get("limit", 0))
                window_seconds = float(row.get("window_seconds", 0.0))
                if limit <= 0 or window_seconds <= 0:
                    continue
                configs[(venue_name, endpoint_name)] = RateLimitConfig(
                    limit=limit,
                    window_seconds=window_seconds,
                )
        return configs

    @staticmethod
    def _order_intent_fingerprint(order: OrderRequest) -> str:
        payload = {
            "symbol": str(order.symbol),
            "side": str(order.side).lower(),
            "quantity": round(float(order.quantity), 10),
            "order_type": str(order.order_type.value),
            "price": None if order.price is None else round(float(order.price), 10),
            "stop_price": None if order.stop_price is None else round(float(order.stop_price), 10),
            "strategy_id": str(order.strategy_id),
            "time_in_force": str(order.time_in_force),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _idempotency_state_key(client_order_id: str, fingerprint: str) -> str:
        return f"idempotency:{str(client_order_id)}:{str(fingerprint)}"

    def set_capital(self, capital: float, source: str = "manual"):
        """
        Set capital - NOT hardcoded.

        Args:
            capital: Total capital in USD
            source: Where capital came from (e.g., 'broker_account', 'config')
        """
        self._capital = capital
        self.risk_engine.risk_monitor.set_capital(capital, source=source)
        logger.info(f"Capital set: ${capital:,.2f} (source: {source})")

    def get_capital(self) -> float:
        """Get capital - raises if not set."""
        if self._capital is None:
            raise RuntimeError(
                "Capital not set. Call set_capital() before trading. "
                "Capital must be injected, never hardcoded."
            )
        return self._capital

    def _active_emergency_state(self) -> Optional[Tuple[RiskDecision, str]]:
        """Return active emergency decision if router is currently halted/flattening."""
        if self.risk_engine.is_flattening:
            return RiskDecision.FLATTEN, "Router currently flattening positions"
        if self.risk_engine.is_halted:
            return RiskDecision.HALT, "Router currently halted by risk overlay"
        return None

    def _post_trade_position_pct(
        self,
        *,
        order: OrderRequest,
        portfolio: Dict[str, Any],
        fallback_price: float,
        capital: float,
    ) -> float:
        """Estimate post-trade absolute symbol exposure as a capital fraction."""
        if capital <= 0:
            return float("inf")

        side = str(order.side).lower()
        delta_qty = float(order.quantity)
        if side == "sell":
            delta_qty = -delta_qty

        current_qty = float((portfolio.get("positions", {}) or {}).get(order.symbol, 0.0))
        post_qty = current_qty + delta_qty

        position_prices = portfolio.get("prices", {}) or {}
        position_price = float(position_prices.get(order.symbol, fallback_price) or fallback_price)
        if position_price <= 0:
            return float("inf")

        post_notional = abs(post_qty) * position_price
        return float(post_notional / capital)

    @staticmethod
    def _estimate_queue_ahead_qty(
        *,
        side: str,
        route_order_type: OrderType,
        market_data: Dict[str, Any],
    ) -> float:
        """
        Estimate queue ahead quantity from top-of-book for passive (limit) orders.

        Market/IOC style orders are assumed to cross the spread immediately.
        """
        if route_order_type != OrderType.LIMIT:
            return 0.0

        order_book = market_data.get("order_book", {})
        if not isinstance(order_book, dict):
            return 0.0

        side_token = str(side).lower()
        if side_token == "buy":
            levels = order_book.get("bids", []) or []
        else:
            levels = order_book.get("asks", []) or []

        if not levels:
            return 0.0
        try:
            return float(max(float(levels[0][1]), 0.0))
        except (TypeError, ValueError, IndexError):
            return 0.0

    def _check_rate_limit(self, *, venue: str, endpoint: str) -> Dict[str, Any]:
        venue_name = str(venue).strip().lower()
        endpoint_name = str(endpoint).strip().lower()
        decision = self.rate_limit_tracker.request(venue_name, endpoint_name)
        key = f"{venue_name}:{endpoint_name}"
        if not decision.allowed:
            self._rate_limit_denials[key] = int(self._rate_limit_denials.get(key, 0)) + 1
        return {
            "venue": venue_name,
            "endpoint": endpoint_name,
            "allowed": bool(decision.allowed),
            "remaining": int(decision.remaining),
            "retry_after_seconds": float(decision.retry_after_seconds),
        }

    async def submit_order(
        self,
        order: OrderRequest,
        market_data: Dict,
        portfolio: Dict,
        strategy_returns: Dict[str, Any],
        portfolio_changes: List[float],
    ) -> OrderResult:
        """Serialized order-admission wrapper that prevents race-condition bypass."""
        async with self._submit_order_lock:
            result = await self._submit_order_unlocked(
                order=order,
                market_data=market_data,
                portfolio=portfolio,
                strategy_returns=strategy_returns,
                portfolio_changes=portfolio_changes,
            )
            self._record_order_ledger(order=order, result=result)
            return result

    def _record_order_ledger(self, *, order: OrderRequest, result: OrderResult) -> None:
        """
        Mirror router result into immutable order-lifecycle ledger.

        Any ledger exception is contained and logged so execution flow is not
        blocked by observability persistence issues.
        """
        audit = result.audit_log if isinstance(result.audit_log, dict) else {}
        order_id = str(result.order_id or audit.get("order_id", "")).strip()
        if not order_id:
            return

        venue = str(result.exchange or (audit.get("routing", {}) or {}).get("exchange", "unknown"))
        requested_qty = float(order.quantity)
        side = str(order.side).lower()
        symbol = str(order.symbol)
        submitted_meta = {
            "order_type": str(order.order_type.value),
            "price": float(order.price or 0.0),
        }

        try:
            self.order_ledger.record(
                order_id=order_id,
                state="submitted",
                symbol=symbol,
                side=side,
                venue=venue,
                quantity=requested_qty,
                metadata=submitted_meta,
            )

            if not result.success:
                self.order_ledger.record(
                    order_id=order_id,
                    state="rejected",
                    symbol=symbol,
                    side=side,
                    venue=venue,
                    quantity=0.0,
                    metadata={
                        "reason": str(result.rejected_reason or audit.get("reject_reason", ""))
                    },
                )
                return

            self.order_ledger.record(
                order_id=order_id,
                state="acknowledged",
                symbol=symbol,
                side=side,
                venue=venue,
                quantity=requested_qty,
                metadata={"decision": str(result.decision.value)},
            )

            fill = audit.get("fill", {}) if isinstance(audit.get("fill"), dict) else {}
            executed_qty = float(fill.get("executed_qty", requested_qty))
            fill_meta = {
                "executed_price": float(fill.get("executed_price", 0.0)),
                "fill_ratio": float(executed_qty / max(requested_qty, 1e-12)),
            }
            if executed_qty + 1e-12 < requested_qty:
                self.order_ledger.record(
                    order_id=order_id,
                    state="partially_filled",
                    symbol=symbol,
                    side=side,
                    venue=venue,
                    quantity=executed_qty,
                    metadata={
                        **fill_meta,
                        "remaining_qty": float(max(requested_qty - executed_qty, 0.0)),
                    },
                )
            else:
                self.order_ledger.record(
                    order_id=order_id,
                    state="filled",
                    symbol=symbol,
                    side=side,
                    venue=venue,
                    quantity=executed_qty,
                    metadata=fill_meta,
                )
        except Exception as exc:
            logger.warning("Order ledger update failed for %s: %s", order_id, exc)

    async def _submit_order_unlocked(
        self,
        order: OrderRequest,
        market_data: Dict,
        portfolio: Dict,
        strategy_returns: Dict[str, Any],
        portfolio_changes: List[float],
    ) -> OrderResult:
        """
        Submit an order with mandatory risk checking.

        This is the ONLY order submission method. All orders must pass through here.

        Args:
            order: OrderRequest with symbol, side, quantity, etc.
            market_data: Current market data for risk assessment
            portfolio: Current portfolio state
            strategy_returns: Returns by strategy for correlation check
            portfolio_changes: Recent P&L changes for VaR calc

        Returns:
            OrderResult with success/failure, risk decision, and audit trail
        """
        self.order_count += 1
        audit_entry = {
            "order_id": f"ord_{self.order_count}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "order": {
                "symbol": order.symbol,
                "side": order.side,
                "quantity": order.quantity,
                "type": order.order_type.value,
                "price": order.price,
                "strategy_id": str(order.strategy_id),
                "expected_alpha_bps": float(getattr(order, "expected_alpha_bps", 0.0) or 0.0),
            },
        }

        # =========================================================================
        # STEP 1: MANDATORY PRE-TRADE RISK CHECK
        # =========================================================================
        # THIS CANNOT BE BYPASSED. EVER.

        try:
            capital = self.get_capital()
        except RuntimeError as e:
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"RISK_ERROR: {str(e)}"
            self.audit_log.append(audit_entry)
            self.reject_count += 1

            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=None,
                order_id=None,
                exchange=None,
                rejected_reason=str(e),
                audit_log=audit_entry,
            )

        emergency_state = self._active_emergency_state()
        if emergency_state is not None:
            decision, reason = emergency_state
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"{decision.value.upper()}: {reason}"
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=decision,
                risk_state=None,
                order_id=None,
                exchange=None,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        client_order_id = str(getattr(order, "client_order_id", "") or "").strip()
        intent_fingerprint = self._order_intent_fingerprint(order)
        audit_entry["idempotency"] = {
            "client_order_id": client_order_id,
            "fingerprint": intent_fingerprint,
            "required_for_live": bool(self.require_live_client_order_id),
        }
        if (
            bool(self.broker_config.get("live_execution", False))
            and self.require_live_client_order_id
            and not client_order_id
        ):
            self._live_idempotency_rejects += 1
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = "LIVE_REQUIRES_CLIENT_ORDER_ID"
            audit_entry["idempotency"]["decision"] = "rejected_missing_client_order_id"
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=None,
                order_id=None,
                exchange=None,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        if client_order_id:
            state_key = self._idempotency_state_key(client_order_id, intent_fingerprint)
            duplicate = self.idempotency_guard.seen(client_order_id, intent_fingerprint) or bool(
                self.distributed_ops_state.seen_recently(state_key)
            )
            if duplicate:
                self._live_idempotency_rejects += 1
                self.reject_count += 1
                audit_entry["rejected"] = True
                audit_entry["reject_reason"] = (
                    f"IDEMPOTENCY_DUPLICATE: client_order_id={client_order_id}"
                )
                audit_entry["idempotency"]["decision"] = "rejected_duplicate"
                self.audit_log.append(audit_entry)
                return OrderResult(
                    success=False,
                    decision=RiskDecision.HALT,
                    risk_state=None,
                    order_id=None,
                    exchange=None,
                    rejected_reason=audit_entry["reject_reason"],
                    audit_log=audit_entry,
                )
            self.idempotency_guard.register(client_order_id, intent_fingerprint)
            self.distributed_ops_state.put(
                state_key,
                {
                    "order_id": str(audit_entry["order_id"]),
                    "timestamp": str(audit_entry["timestamp"]),
                },
            )
            audit_entry["idempotency"]["decision"] = "accepted"
        else:
            audit_entry["idempotency"]["decision"] = "skipped_no_client_order_id"

        requested_quantity = float(order.quantity)
        throttled_qty, regime_decision = self.regime_overlay.throttle_quantity(
            order.symbol,
            requested_quantity,
            market_data,
        )
        order.quantity = float(throttled_qty)
        audit_entry["regime_overlay"] = {
            "regime": regime_decision.regime,
            "reason": regime_decision.reason,
            "multiplier": regime_decision.multiplier,
            "requested_quantity": requested_quantity,
            "approved_quantity": float(order.quantity),
        }
        if order.quantity <= 0:
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = "REGIME_OVERLAY: quantity throttled to zero"
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=None,
                order_id=None,
                exchange=None,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        # Calculate notional
        price = order.price or market_data.get("last_price", 0)
        notional = order.quantity * price

        # Build portfolio state for risk check
        from risk.kill_switches import PortfolioState

        portfolio_state = PortfolioState(
            timestamp=datetime.now(),
            positions=portfolio.get("positions", {}),
            prices=portfolio.get("prices", {}),
            total_pnl=portfolio.get("total_pnl", 0),
            unrealized_pnl=portfolio.get("unrealized_pnl", 0),
            realized_pnl=portfolio.get("realized_pnl", 0),
            gross_exposure=portfolio.get("gross_exposure", 0),
            net_exposure=portfolio.get("net_exposure", 0),
            leverage=portfolio.get("leverage", 0),
            open_orders=portfolio.get("open_orders", []),
            pending_cancels=[],
        )

        # MANDATORY: Pre-trade risk check
        decision, risk_state = self.risk_engine.pre_trade_check(
            {
                "notional": notional,
                "symbol": order.symbol,
                "side": order.side,
                "quantity": order.quantity,
            },
            portfolio_state,
            strategy_returns,
            portfolio_changes,
        )

        audit_entry["risk_check"] = {
            "decision": decision.value,
            "reason": risk_state.reason,
            "limits": {
                "max_order": risk_state.max_order_notional,
                "max_leverage": risk_state.max_gross_leverage,
                "max_participation": risk_state.max_participation,
            },
        }

        # =========================================================================
        # RISK DECISION HANDLING
        # =========================================================================

        if decision == RiskDecision.FLATTEN:
            # CRITICAL: System is in emergency mode
            logger.critical(f"ORDER REJECTED - FLATTEN ACTIVE: {risk_state.reason}")
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"FLATTEN: {risk_state.reason}"
            self.audit_log.append(audit_entry)

            # Cancel any existing orders
            self.risk_engine._initiate_flatten(portfolio_state)

            return OrderResult(
                success=False,
                decision=decision,
                risk_state=risk_state,
                order_id=None,
                exchange=None,
                rejected_reason=f"FLATTEN: {risk_state.reason}",
                audit_log=audit_entry,
            )

        if decision == RiskDecision.HALT:
            logger.warning(f"ORDER REJECTED - HALT: {risk_state.reason}")
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"HALT: {risk_state.reason}"
            self.audit_log.append(audit_entry)

            return OrderResult(
                success=False,
                decision=decision,
                risk_state=risk_state,
                order_id=None,
                exchange=None,
                rejected_reason=f"HALT: {risk_state.reason}",
                audit_log=audit_entry,
            )

        if decision == RiskDecision.REDUCE:
            # Reduce order size
            reduction_factor = 0.5
            original_qty = order.quantity
            order.quantity *= reduction_factor
            logger.warning(f"Order reduced from {original_qty} to {order.quantity} due to risk")
            audit_entry["modified"] = {
                "original_quantity": original_qty,
                "new_quantity": order.quantity,
                "reason": risk_state.reason,
            }

            # Recalculate notional
            notional = order.quantity * price

        # Check order size against risk limits
        if notional > risk_state.max_order_notional:
            logger.warning(
                f"Order notional ${notional:,.0f} > limit ${risk_state.max_order_notional:,.0f}"
            )
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = (
                f"OVERSIZED: {notional:,.0f} > {risk_state.max_order_notional:,.0f}"
            )
            self.audit_log.append(audit_entry)

            return OrderResult(
                success=False,
                decision=decision,
                risk_state=risk_state,
                order_id=None,
                exchange=None,
                rejected_reason="Order size exceeds risk limit",
                audit_log=audit_entry,
            )

        post_trade_position_pct = self._post_trade_position_pct(
            order=order,
            portfolio=portfolio,
            fallback_price=float(price),
            capital=float(capital),
        )
        audit_entry["risk_check"]["post_trade_position_pct"] = float(post_trade_position_pct)
        audit_entry["risk_check"]["max_single_position_pct"] = float(
            self.risk_limits.max_single_position_pct
        )
        if post_trade_position_pct > float(self.risk_limits.max_single_position_pct):
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = (
                "POSITION_LIMIT: "
                f"{post_trade_position_pct:.4f} > {float(self.risk_limits.max_single_position_pct):.4f}"
            )
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=risk_state,
                order_id=None,
                exchange=None,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        # Capacity controls (capital/capacity realism)
        symbol_caps = self.broker_config.get("max_symbol_notional", {})
        symbol_cap = symbol_caps.get(order.symbol)
        if symbol_cap is not None and notional > float(symbol_cap):
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"SYMBOL_CAP: {notional:.2f} > {float(symbol_cap):.2f}"
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=risk_state,
                order_id=None,
                exchange=None,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        # =========================================================================
        # STEP 2: SMART ROUTING
        # =========================================================================

        route = await self.smart_router.route_order(order, market_data)
        ranked_exchanges = list(route.ranked_exchanges or [route.exchange])
        failover_target = self.reliability_monitor.choose_failover(
            primary_venue=route.exchange,
            candidates=ranked_exchanges,
        )
        if failover_target is not None and failover_target != route.exchange:
            previous_exchange = route.exchange
            route.exchange = failover_target
            audit_entry["routing_failover"] = {
                "from_exchange": previous_exchange,
                "to_exchange": failover_target,
            }
        elif self.reliability_monitor.is_degraded(route.exchange):
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"DEGRADED_VENUE_NO_FAILOVER: {route.exchange}"
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=risk_state,
                order_id=None,
                exchange=route.exchange,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        audit_entry["routing"] = {
            "exchange": route.exchange,
            "order_type": route.order_type.value,
            "expected_cost": route.expected_cost,
            "expected_slippage": route.expected_slippage,
            "ranked_exchanges": ranked_exchanges,
        }
        expected_alpha_bps = self._resolve_expected_alpha_bps(order)
        predicted_total_router_bps = float(
            Bps.from_pct(
                (float(route.expected_cost) + float(route.expected_slippage)) / max(notional, 1e-12)
            )
        )
        predicted_net_alpha_bps = float(expected_alpha_bps - predicted_total_router_bps)

        capacity_decision = self.capacity_model.evaluate_order(
            strategy_id=str(order.strategy_id),
            venue=route.exchange,
            symbol=order.symbol,
            candidate_notional_usd=float(notional),
            predicted_net_alpha_bps=predicted_net_alpha_bps,
        )
        audit_entry["capacity_curve"] = {
            "strategy_id": str(order.strategy_id),
            "requested_notional_usd": float(notional),
            "approved_notional_usd": float(capacity_decision.approved_notional_usd),
            "throttle_ratio": float(capacity_decision.throttle_ratio),
            "marginal_net_alpha_bps": float(capacity_decision.marginal_net_alpha_bps),
            "reason": capacity_decision.reason,
            "blocked": bool(capacity_decision.blocked),
            "points_used": int(capacity_decision.points_used),
            "expected_alpha_bps": float(expected_alpha_bps),
            "predicted_total_router_bps": float(predicted_total_router_bps),
            "predicted_net_alpha_bps": float(predicted_net_alpha_bps),
        }

        if capacity_decision.blocked:
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"CAPACITY_CURVE_BLOCK: {capacity_decision.reason}"
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=risk_state,
                order_id=None,
                exchange=route.exchange,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        approved_notional = float(capacity_decision.approved_notional_usd)
        if approved_notional + 1e-9 < float(notional):
            original_quantity = float(order.quantity)
            order.quantity = float(max(approved_notional / max(float(price), 1e-12), 0.0))
            notional = float(order.quantity * float(price))
            audit_entry.setdefault("modified", {})
            audit_entry["modified"]["capacity_curve"] = {
                "original_quantity": original_quantity,
                "new_quantity": float(order.quantity),
                "reason": capacity_decision.reason,
            }
            if order.quantity <= 0 or notional <= 0:
                self.reject_count += 1
                audit_entry["rejected"] = True
                audit_entry["reject_reason"] = "CAPACITY_CURVE: quantity throttled to zero"
                self.audit_log.append(audit_entry)
                return OrderResult(
                    success=False,
                    decision=RiskDecision.HALT,
                    risk_state=risk_state,
                    order_id=None,
                    exchange=route.exchange,
                    rejected_reason=audit_entry["reject_reason"],
                    audit_log=audit_entry,
                )

        venue_caps = self.broker_config.get("max_venue_notional", {})
        venue_cap = venue_caps.get(route.exchange)
        if venue_cap is not None and notional > float(venue_cap):
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"VENUE_CAP: {notional:.2f} > {float(venue_cap):.2f}"
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=risk_state,
                order_id=None,
                exchange=route.exchange,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        shorting_decision = self.shorting_overlay.evaluate(
            symbol=order.symbol,
            venue=route.exchange,
            side=order.side,
            order_qty=float(order.quantity),
            order_price=float(price),
            portfolio=portfolio,
            capital=float(capital),
        )
        audit_entry["shorting_overlay"] = shorting_decision.to_dict()
        if not shorting_decision.approved:
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"SHORTING_CONTROL: {shorting_decision.reason}"
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=risk_state,
                order_id=None,
                exchange=route.exchange,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        # =========================================================================
        # STEP 3: COST ESTIMATION (via RealisticCostModel)
        # =========================================================================
        cost_breakdown = None
        spread_bps = 0.0
        depth_1pct_usd = 0.0

        # Build order book from market data
        if "order_book" in market_data:
            ob_data = market_data["order_book"]
            bids = [OrderBookLevel(Price(p), Quantity(s)) for p, s in ob_data.get("bids", [])]
            asks = [OrderBookLevel(Price(p), Quantity(s)) for p, s in ob_data.get("asks", [])]
            order_book = OrderBook(bids=bids, asks=asks)

            side_enum = Side.BUY if order.side == "buy" else Side.SELL

            cost_breakdown = self.cost_model.calculate_total_cost(
                NotionalUSD(notional),
                Price(price),
                order_book,
                side_enum,
                is_maker=(route.order_type == OrderType.LIMIT),
            )

            depth_summary = order_book.get_depth_summary()
            spread_bps = float(depth_summary["spread_bps"])
            depth_1pct_usd = float(depth_summary["min_depth_1pct_usd"])

            audit_entry["cost_estimate"] = cost_breakdown.to_dict()
            audit_entry["market_microstructure"] = {
                "spread_bps": spread_bps,
                "depth_1pct_usd": depth_1pct_usd,
            }

        # =========================================================================
        # STEP 4: ORDER EXECUTION
        # =========================================================================
        order_id = audit_entry["order_id"]
        live_order_response = None
        execution_start = time.perf_counter()
        if self.broker_config.get("live_execution", False):
            live_order_response = await self._place_live_order(route=route, order=order)
            if live_order_response is None:
                latency_ms = (time.perf_counter() - execution_start) * 1000.0
                self.reliability_monitor.record(
                    venue=route.exchange,
                    latency_ms=latency_ms,
                    rejected=True,
                    failed=True,
                )
                self.reject_count += 1
                audit_entry["rejected"] = True
                audit_entry["reject_reason"] = str(
                    self._last_live_order_error or f"LIVE_EXECUTION_FAILED: {route.exchange}"
                )
                if self._last_live_order_controls:
                    audit_entry["live_controls"] = dict(self._last_live_order_controls)
                audit_entry["execution_quality"] = {
                    "latency_ms": latency_ms,
                    "failed": True,
                }
                self.audit_log.append(audit_entry)
                return OrderResult(
                    success=False,
                    decision=RiskDecision.HALT,
                    risk_state=risk_state,
                    order_id=None,
                    exchange=route.exchange,
                    rejected_reason=audit_entry["reject_reason"],
                    audit_log=audit_entry,
                )

        fill = await self.fill_provider.get_fill(
            order_id=order_id,
            symbol=order.symbol,
            venue=route.exchange,
            side=order.side,
            requested_qty=float(order.quantity),
            reference_price=float(price),
            order_book=market_data.get("order_book", {}),
            queue_ahead_qty=self._estimate_queue_ahead_qty(
                side=order.side,
                route_order_type=route.order_type,
                market_data=market_data,
            ),
        )
        logger.info(
            "Order %s filled: %s %s qty=%.6f @ %.6f on %s",
            order_id,
            fill.symbol,
            order.side,
            fill.executed_qty,
            fill.executed_price,
            fill.venue,
        )
        execution_latency_ms = (time.perf_counter() - execution_start) * 1000.0
        if fill.executed_qty <= 0 or fill.executed_price <= 0:
            self.reliability_monitor.record(
                venue=route.exchange,
                latency_ms=execution_latency_ms,
                rejected=True,
                failed=True,
            )
            self.reject_count += 1
            audit_entry["rejected"] = True
            audit_entry["reject_reason"] = f"NO_FILL: {route.exchange}"
            audit_entry["execution_quality"] = {
                "latency_ms": execution_latency_ms,
                "failed": True,
            }
            self.audit_log.append(audit_entry)
            return OrderResult(
                success=False,
                decision=RiskDecision.HALT,
                risk_state=risk_state,
                order_id=None,
                exchange=route.exchange,
                rejected_reason=audit_entry["reject_reason"],
                audit_log=audit_entry,
            )

        audit_entry["executed"] = True
        audit_entry["order_id"] = order_id
        audit_entry["fill"] = {
            "executed_price": fill.executed_price,
            "executed_qty": fill.executed_qty,
            "timestamp": fill.timestamp.isoformat(),
            "venue": fill.venue,
            "symbol": fill.symbol,
        }
        if live_order_response is not None:
            audit_entry["live_order_response"] = live_order_response
        if self._last_live_order_controls:
            audit_entry["live_controls"] = dict(self._last_live_order_controls)
        self.audit_log.append(audit_entry)

        # =========================================================================
        # STEP 5: POST-TRADE LOGGING (TCA)
        # =========================================================================
        # Feed into TCA for cost model calibration
        tca_payload = self._update_tca(
            order_id=order_id,
            audit_entry=audit_entry,
            order=order,
            fill=fill,
            notional=float(notional),
            reference_price=float(price),
            route=route,
            cost_breakdown=cost_breakdown,
            spread_bps=spread_bps,
            depth_1pct_usd=depth_1pct_usd,
            vol_24h=float(market_data.get("vol_24h", self.cost_model.base_vol)),
            expected_alpha_bps=float(expected_alpha_bps),
        )
        requested_qty = float(max(order.quantity, 1e-12))
        fill_ratio = float(fill.executed_qty) / requested_qty
        realized_notional = float(fill.executed_price) * float(fill.executed_qty)
        self.smart_router.record_executed_notional(
            route.exchange,
            realized_notional,
            timestamp=fill.timestamp,
        )
        self.smart_router.record_execution_outcome(
            exchange=route.exchange,
            symbol=order.symbol,
            expected_slippage_bps=float(tca_payload.get("predicted_slippage_bps", 0.0)),
            realized_slippage_bps=float(tca_payload.get("realized_slippage_bps", 0.0)),
            fill_ratio=fill_ratio,
            latency_ms=execution_latency_ms,
        )
        self.reliability_monitor.record(
            venue=route.exchange,
            latency_ms=execution_latency_ms,
            rejected=False,
            failed=False,
        )
        self.capacity_model.record(
            strategy_id=str(order.strategy_id),
            venue=route.exchange,
            symbol=order.symbol,
            notional_usd=float(realized_notional),
            net_alpha_bps=float(tca_payload.get("realized_net_alpha_bps", 0.0)),
            timestamp=fill.timestamp,
        )
        audit_entry["execution_quality"] = {
            "latency_ms": execution_latency_ms,
            "fill_ratio": fill_ratio,
            "reliability_degraded": self.reliability_monitor.is_degraded(route.exchange),
        }

        return OrderResult(
            success=True,
            decision=decision,
            risk_state=risk_state,
            order_id=order_id,
            exchange=route.exchange,
            rejected_reason=None,
            audit_log=audit_entry,
        )

    def _update_tca(
        self,
        *,
        order_id: str,
        audit_entry: Dict,
        order: OrderRequest,
        fill: ExecutionFill,
        notional: float,
        reference_price: float,
        route: RouteDecision,
        cost_breakdown,
        spread_bps: float,
        depth_1pct_usd: float,
        vol_24h: float,
        expected_alpha_bps: float,
    ) -> Dict[str, float]:
        """Persist predicted vs. realized slippage/costs for TCA calibration."""
        if notional <= 0 or reference_price <= 0:
            logger.warning("TCA skipped for %s due to invalid notional/price.", order_id)
            return {
                "predicted_slippage_bps": 0.0,
                "realized_slippage_bps": 0.0,
                "predicted_total_bps": 0.0,
                "realized_total_bps": 0.0,
            }

        if cost_breakdown is not None:
            predicted_slippage_bps = float(Bps.from_pct(float(cost_breakdown.slippage) / notional))
            predicted_commission_bps = float(
                Bps.from_pct(float(cost_breakdown.commission) / notional)
            )
            predicted_total_bps = float(cost_breakdown.total_bps)
        else:
            predicted_slippage_bps = float(Bps.from_pct(route.expected_slippage / notional))
            predicted_commission_bps = float(Bps.from_pct(self.cost_model.commission))
            predicted_total_bps = predicted_slippage_bps + predicted_commission_bps

        if order.side == "buy":
            realized_slippage_pct = max(
                (fill.executed_price - reference_price) / reference_price, 0.0
            )
        else:
            realized_slippage_pct = max(
                (reference_price - fill.executed_price) / reference_price, 0.0
            )

        realized_slippage_bps = float(Bps.from_pct(realized_slippage_pct))
        realized_commission_bps = float(Bps.from_pct(self.cost_model.commission))
        realized_total_bps = realized_slippage_bps + realized_commission_bps

        realized_notional = float(fill.executed_price) * float(fill.executed_qty)
        record = TCATradeRecord(
            trade_id=order_id,
            timestamp=fill.timestamp,
            symbol=fill.symbol,
            exchange=fill.venue,
            side=order.side,
            quantity=float(fill.executed_qty),
            price=float(fill.executed_price),
            notional=realized_notional,
            predicted_slippage_bps=predicted_slippage_bps,
            predicted_commission_bps=predicted_commission_bps,
            predicted_total_bps=predicted_total_bps,
            realized_slippage_bps=realized_slippage_bps,
            realized_commission_bps=realized_commission_bps,
            realized_total_bps=realized_total_bps,
            spread_bps=spread_bps,
            vol_24h=vol_24h,
            depth_1pct_usd=depth_1pct_usd,
            strategy_id=str(order.strategy_id),
            expected_alpha_bps=float(expected_alpha_bps),
        )
        self.tca_db.add_record(record)
        self.tca_db.save()
        realized_net_alpha_bps = float(expected_alpha_bps) - realized_total_bps

        audit_entry["tca"] = {
            "predicted_slippage_bps": predicted_slippage_bps,
            "realized_slippage_bps": realized_slippage_bps,
            "predicted_total_bps": predicted_total_bps,
            "realized_total_bps": realized_total_bps,
            "strategy_id": str(order.strategy_id),
            "expected_alpha_bps": float(expected_alpha_bps),
            "realized_net_alpha_bps": realized_net_alpha_bps,
        }
        logger.info(
            "TCA %s %s@%s strategy=%s: predicted_slip=%.3f bps realized_slip=%.3f bps net_alpha=%.3f bps",
            order_id,
            fill.symbol,
            fill.venue,
            str(order.strategy_id),
            predicted_slippage_bps,
            realized_slippage_bps,
            realized_net_alpha_bps,
        )
        return {
            "predicted_slippage_bps": predicted_slippage_bps,
            "realized_slippage_bps": realized_slippage_bps,
            "predicted_total_bps": predicted_total_bps,
            "realized_total_bps": realized_total_bps,
            "expected_alpha_bps": float(expected_alpha_bps),
            "realized_net_alpha_bps": realized_net_alpha_bps,
        }

    def _create_token(self) -> "_RouterToken":
        """
        Private factory for creating RouterToken.

        Only RiskAwareRouter can create tokens. Adapters must verify
        received token using: type(token) is _RouterToken
        """
        return _create_router_token(id(self))

    def configure_market_adapters(self, markets_config: Dict[str, Any]) -> None:
        """
        Build adapter registry for enabled markets.

        Engine code must not import adapter modules directly; this router
        owns all adapter construction and access.
        """
        self.market_venues.clear()
        self._markets_config = markets_config or {}

        crypto_cfg = self._markets_config.get("crypto", {})
        if crypto_cfg.get("enabled", False):
            for venue in crypto_cfg.get("exchanges", []):
                self._register_venue(
                    market="crypto",
                    venue_name=venue.get("name", "crypto_stub"),
                    symbols=venue.get("symbols", []),
                    raw_config=venue,
                )

        equities_cfg = self._markets_config.get("equities", {})
        if equities_cfg.get("enabled", False):
            for venue in equities_cfg.get("brokers", []):
                self._register_venue(
                    market="equities",
                    venue_name=venue.get("name", "equities_stub"),
                    symbols=venue.get("symbols", []),
                    raw_config=venue,
                )

        forex_cfg = self._markets_config.get("forex", {})
        if forex_cfg.get("enabled", False):
            for venue in forex_cfg.get("brokers", []):
                self._register_venue(
                    market="forex",
                    venue_name=venue.get("name", "forex_stub"),
                    symbols=venue.get("pairs", []),
                    raw_config=venue,
                )

        logger.info("Configured %s market venues", len(self.market_venues))

    def _resolve_secret(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if text.startswith("${") and text.endswith("}"):
            key = text[2:-1].strip()
            return os.getenv(key)
        return text

    def _register_venue(
        self,
        *,
        market: str,
        venue_name: str,
        symbols: List[str],
        raw_config: Dict[str, Any],
    ) -> None:
        adapter = self._build_adapter(market=market, venue_name=venue_name, cfg=raw_config)
        self.market_venues[venue_name] = VenueClient(
            market=market,
            venue=venue_name,
            symbols=list(symbols),
            adapter=adapter,
            connected=False,
            is_stub=(adapter is None),
        )

    def _build_adapter(self, *, market: str, venue_name: str, cfg: Dict[str, Any]) -> Optional[Any]:
        """
        Construct venue adapters with router token enforcement.

        Missing credentials keep the venue in deterministic stub mode.
        """
        venue = venue_name.lower()
        try:
            if market == "crypto" and venue == "binance":
                from markets.crypto.binance_adapter import BinanceAdapter

                api_key = self._resolve_secret(cfg.get("api_key"))
                api_secret = self._resolve_secret(cfg.get("api_secret"))
                if not api_key or not api_secret:
                    return None
                return BinanceAdapter(
                    api_key=api_key,
                    api_secret=api_secret,
                    router_token=self._router_token,
                    testnet=bool(cfg.get("testnet", True)),
                )

            if market == "crypto" and venue == "coinbase":
                from markets.crypto.coinbase_adapter import CoinbaseAdapter

                api_key = self._resolve_secret(cfg.get("api_key"))
                api_secret = self._resolve_secret(cfg.get("api_secret"))
                passphrase = self._resolve_secret(cfg.get("passphrase"))
                if not api_key or not api_secret or not passphrase:
                    return None
                return CoinbaseAdapter(
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=passphrase,
                    router_token=self._router_token,
                    sandbox=bool(cfg.get("sandbox", True)),
                )

            if market == "equities" and venue == "alpaca":
                from markets.equities.alpaca_adapter import AlpacaAdapter

                api_key = self._resolve_secret(cfg.get("api_key"))
                api_secret = self._resolve_secret(cfg.get("api_secret"))
                if not api_key or not api_secret:
                    return None
                return AlpacaAdapter(
                    api_key=api_key,
                    api_secret=api_secret,
                    router_token=self._router_token,
                    paper=bool(cfg.get("paper", True)),
                )

            if market == "forex" and venue == "oanda":
                from markets.forex.oanda_adapter import OandaAdapter

                api_key = self._resolve_secret(cfg.get("api_key"))
                account_id = self._resolve_secret(cfg.get("account_id"))
                if not api_key or not account_id:
                    return None
                return OandaAdapter(
                    api_key=api_key,
                    account_id=account_id,
                    router_token=self._router_token,
                    practice=bool(cfg.get("practice", True)),
                )
        except Exception as exc:
            logger.warning("Adapter construction failed for %s/%s: %s", market, venue_name, exc)
            return None

        return None

    async def start_market_data(self) -> None:
        """Connect all live adapters; keep failed ones as stubs."""
        for venue in self.market_venues.values():
            if venue.adapter is None:
                venue.is_stub = True
                continue
            try:
                await venue.adapter.connect()
                venue.connected = True
                venue.is_stub = False
                logger.info("Connected venue adapter: %s", venue.venue)
            except Exception as exc:
                venue.connected = False
                venue.is_stub = True
                logger.warning("Adapter connect failed for %s (stub mode): %s", venue.venue, exc)

    async def stop_market_data(self) -> None:
        """Disconnect venue adapters."""
        for venue in self.market_venues.values():
            if venue.adapter is None or not venue.connected:
                continue
            try:
                await venue.adapter.disconnect()
            except Exception:
                pass
            venue.connected = False

    def get_market_registry(self) -> Dict[str, Dict[str, Any]]:
        """Expose configured venue metadata for engine-level observability."""
        registry: Dict[str, Dict[str, Any]] = {}
        for venue_name, venue in self.market_venues.items():
            registry[venue_name] = {
                "market": venue.market,
                "venue": venue_name,
                "symbols": list(venue.symbols),
                "connected": venue.connected,
                "stub": venue.is_stub,
            }
        return registry

    def get_stream_registry(self) -> Dict[str, Dict[str, Any]]:
        """
        Expose configured stream descriptors per venue.

        Adapters provide canonical `market/order/fill` endpoints for parity
        monitoring and future stream-worker wiring.
        """
        registry: Dict[str, Dict[str, Any]] = {}
        for venue_name, venue in self.market_venues.items():
            if venue.adapter is None or not hasattr(venue.adapter, "stream_descriptors"):
                registry[venue_name] = {"available": False, "reason": "adapter_unavailable"}
                continue

            try:
                descriptors = venue.adapter.stream_descriptors()
            except Exception as exc:
                registry[venue_name] = {
                    "available": False,
                    "reason": f"descriptor_error:{exc}",
                }
                continue

            registry[venue_name] = {
                "available": True,
                "market": venue.market,
                "connected": bool(venue.connected),
                "stub": bool(venue.is_stub),
                "streams": descriptors,
            }
        return registry

    async def fetch_market_snapshot(self) -> Dict[str, Any]:
        """
        Fetch a unified market snapshot keyed by venue for smart routing.

        Returns a dict containing:
            - venue -> symbol quote maps
            - order_book
            - last_price
            - vol_24h
        """
        snapshot: Dict[str, Any] = {}
        aggregated_prices: List[float] = []
        aggregated_volumes: List[float] = []
        fallback_order_book = None

        for venue_name, venue in self.market_venues.items():
            venue_quotes: Dict[str, Dict[str, float]] = {}
            for symbol in venue.symbols:
                quote = await self._fetch_symbol_quote(venue, symbol)
                if quote is None:
                    quote = self._synthetic_quote(symbol=symbol, venue=venue_name)

                venue_quotes[symbol] = {
                    "price": quote["price"],
                    "spread": quote["spread"],
                    "volume_24h": quote["volume_24h"],
                }
                aggregated_prices.append(quote["price"])
                aggregated_volumes.append(quote["volume_24h"])
                if fallback_order_book is None:
                    fallback_order_book = quote["order_book"]

            if venue_quotes:
                snapshot[venue_name] = venue_quotes

        if not aggregated_prices:
            default_quote = self._synthetic_quote(symbol="DEFAULT", venue="stub")
            aggregated_prices = [default_quote["price"]]
            aggregated_volumes = [default_quote["volume_24h"]]
            fallback_order_book = default_quote["order_book"]

        snapshot["last_price"] = float(sum(aggregated_prices) / len(aggregated_prices))
        snapshot["vol_24h"] = float(sum(aggregated_volumes) / len(aggregated_volumes))
        snapshot["order_book"] = fallback_order_book
        return snapshot

    async def _fetch_symbol_quote(
        self, venue: VenueClient, symbol: str
    ) -> Optional[Dict[str, Any]]:
        if venue.adapter is None or not venue.connected:
            return None

        try:
            if venue.market == "crypto" and venue.venue.lower() == "binance":
                ticker_rl = self._check_rate_limit(venue=venue.venue, endpoint="market_ticker")
                if not ticker_rl["allowed"]:
                    return None
                ticker = await venue.adapter.get_ticker(symbol)
                orderbook_rl = self._check_rate_limit(
                    venue=venue.venue,
                    endpoint="market_order_book",
                )
                if not orderbook_rl["allowed"]:
                    return None
                orderbook = await venue.adapter.get_orderbook(symbol, limit=5)
                bid = float(ticker.get("bidPrice", 0) or 0)
                ask = float(ticker.get("askPrice", 0) or 0)
                price = float(ticker.get("lastPrice", 0) or 0)
                spread = abs(ask - bid) / price if price and ask and bid else 0.001
                return {
                    "price": price or (ask + bid) / 2,
                    "spread": spread,
                    "volume_24h": float(
                        ticker.get("quoteVolume", 0) or ticker.get("volume", 0) or 0
                    ),
                    "order_book": {
                        "bids": [(float(p), float(s)) for p, s in orderbook.get("bids", [])[:5]],
                        "asks": [(float(p), float(s)) for p, s in orderbook.get("asks", [])[:5]],
                    },
                }

            if venue.market == "crypto" and venue.venue.lower() == "coinbase":
                ticker_rl = self._check_rate_limit(venue=venue.venue, endpoint="market_ticker")
                if not ticker_rl["allowed"]:
                    return None
                ticker = await venue.adapter.get_product_ticker(symbol)
                bid = float(ticker.get("bid", 0) or 0)
                ask = float(ticker.get("ask", 0) or 0)
                price = float(ticker.get("price", 0) or 0)
                spread = abs(ask - bid) / price if price and ask and bid else 0.001
                return {
                    "price": price or (ask + bid) / 2,
                    "spread": spread,
                    "volume_24h": float(ticker.get("volume", 0) or 0),
                    "order_book": self._synthetic_order_book(price or (ask + bid) / 2),
                }

            if venue.market == "equities" and venue.venue.lower() == "alpaca":
                quote_rl = self._check_rate_limit(venue=venue.venue, endpoint="market_quote")
                if not quote_rl["allowed"]:
                    return None
                quote = await venue.adapter.get_latest_quote(symbol)
                bid = float(quote.get("bp", 0) or quote.get("bid_price", 0) or 0)
                ask = float(quote.get("ap", 0) or quote.get("ask_price", 0) or 0)
                price = (bid + ask) / 2 if bid and ask else max(bid, ask)
                spread = abs(ask - bid) / price if price and ask and bid else 0.001
                return {
                    "price": price,
                    "spread": spread,
                    "volume_24h": float(quote.get("v", 0) or quote.get("volume", 0) or 0),
                    "order_book": self._synthetic_order_book(price),
                }

            if venue.market == "forex" and venue.venue.lower() == "oanda":
                pricing_rl = self._check_rate_limit(venue=venue.venue, endpoint="market_pricing")
                if not pricing_rl["allowed"]:
                    return None
                pricing = await venue.adapter.get_pricing([symbol])
                if not pricing:
                    return None
                row = pricing[0]
                bid = float(row.get("bids", [{}])[0].get("price", 0) or 0)
                ask = float(row.get("asks", [{}])[0].get("price", 0) or 0)
                price = (bid + ask) / 2 if bid and ask else max(bid, ask)
                spread = abs(ask - bid) / price if price and ask and bid else 0.0002
                return {
                    "price": price,
                    "spread": spread,
                    "volume_24h": float(row.get("tradeable", 1)) * 1_000_000,
                    "order_book": self._synthetic_order_book(price),
                }
        except Exception as exc:
            logger.warning("Quote fetch failed for %s %s: %s", venue.venue, symbol, exc)
            return None

        return None

    def _synthetic_order_book(self, mid_price: float) -> Dict[str, List[Tuple[float, float]]]:
        mid = max(float(mid_price), 1e-6)
        spread = mid * 0.0005
        return {
            "bids": [(mid - spread, 100.0), (mid - 2 * spread, 150.0)],
            "asks": [(mid + spread, 100.0), (mid + 2 * spread, 150.0)],
        }

    def _synthetic_quote(self, *, symbol: str, venue: str) -> Dict[str, Any]:
        key = abs(hash((symbol, venue)))
        base = 50.0 + (key % 5000) / 25.0
        spread_bps = 5 + (key % 15)
        spread = spread_bps / 10000.0
        volume = 500_000.0 + (key % 10_000) * 50.0
        order_book = self._synthetic_order_book(base)
        return {
            "price": base,
            "spread": spread,
            "volume_24h": volume,
            "order_book": order_book,
        }

    async def _place_live_order(
        self, *, route: RouteDecision, order: OrderRequest
    ) -> Optional[Dict[str, Any]]:
        """Send a live order through the configured venue adapter."""
        self._last_live_order_error = None
        self._last_live_order_controls = {}
        venue = self.market_venues.get(route.exchange)
        if venue is None or venue.adapter is None or not venue.connected:
            self._last_live_order_error = f"LIVE_VENUE_UNAVAILABLE: {route.exchange}"
            return None

        try:
            venue_name = venue.venue.lower()
            endpoint = "order_create"
            rate_limit = self._check_rate_limit(venue=venue_name, endpoint=endpoint)
            self._last_live_order_controls = {"rate_limit": rate_limit}
            if not rate_limit["allowed"]:
                self._live_rate_limit_rejects += 1
                self._last_live_order_error = (
                    "RATE_LIMIT_EXCEEDED: "
                    f"{venue_name}/{endpoint} retry_after={rate_limit['retry_after_seconds']:.3f}s"
                )
                logger.warning(self._last_live_order_error)
                return None

            if venue.market == "crypto" and venue_name == "binance":
                return await venue.adapter.place_order(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=route.order_type.value,
                    quantity=float(order.quantity),
                    price=route.price,
                    client_order_id=order.client_order_id,
                    router_token=self._router_token,
                )

            if venue.market == "crypto" and venue_name == "coinbase":
                return await venue.adapter.place_order(
                    product_id=order.symbol,
                    side=order.side,
                    order_type=route.order_type.value,
                    size=float(order.quantity),
                    price=route.price,
                    client_order_id=order.client_order_id,
                    router_token=self._router_token,
                )

            if venue.market == "equities" and venue_name == "alpaca":
                return await venue.adapter.place_order(
                    symbol=order.symbol,
                    qty=float(order.quantity),
                    side=order.side,
                    order_type=route.order_type.value,
                    limit_price=route.price,
                    client_order_id=order.client_order_id,
                    router_token=self._router_token,
                )

            if venue.market == "forex" and venue_name == "oanda":
                units = float(order.quantity if order.side == "buy" else -order.quantity)
                return await venue.adapter.place_order(
                    instrument=order.symbol,
                    units=units,
                    order_type=route.order_type.value.upper(),
                    price=route.price,
                    client_order_id=order.client_order_id,
                    router_token=self._router_token,
                )
        except Exception as exc:
            logger.error("Live order send failed for %s: %s", route.exchange, exc)
            self._last_live_order_error = f"LIVE_EXECUTION_EXCEPTION: {route.exchange}: {exc}"
            return None

        self._last_live_order_error = f"LIVE_EXECUTION_UNSUPPORTED_VENUE: {route.exchange}"
        return None

    async def cancel_live_order(self, *, exchange: str, symbol: str, venue_order_id: str) -> bool:
        """Cancel/close a live venue order or trade with endpoint rate-limit gating."""
        venue = self.market_venues.get(str(exchange))
        if venue is None or venue.adapter is None or not venue.connected:
            return False

        venue_name = venue.venue.lower()
        rate_limit = self._check_rate_limit(venue=venue_name, endpoint="order_cancel")
        self._last_live_order_controls = {"rate_limit": rate_limit}
        if not rate_limit["allowed"]:
            self._live_rate_limit_rejects += 1
            self._last_live_order_error = (
                "RATE_LIMIT_EXCEEDED: "
                f"{venue_name}/order_cancel retry_after={rate_limit['retry_after_seconds']:.3f}s"
            )
            return False

        try:
            if venue.market == "crypto" and venue_name == "binance":
                order_id_token: Any
                try:
                    order_id_token = int(str(venue_order_id))
                except (TypeError, ValueError):
                    order_id_token = str(venue_order_id)
                await venue.adapter.cancel_order(
                    symbol=str(symbol),
                    order_id=order_id_token,
                    router_token=self._router_token,
                )
                return True

            if venue.market == "crypto" and venue_name == "coinbase":
                await venue.adapter.cancel_order(
                    order_id=str(venue_order_id),
                    router_token=self._router_token,
                )
                return True

            if venue.market == "equities" and venue_name == "alpaca":
                await venue.adapter.cancel_order(
                    order_id=str(venue_order_id),
                    router_token=self._router_token,
                )
                return True

            if venue.market == "forex" and venue_name == "oanda":
                await venue.adapter.close_trade(
                    trade_id=str(venue_order_id),
                    router_token=self._router_token,
                )
                return True
        except Exception as exc:
            logger.error("Live order cancel failed for %s: %s", exchange, exc)
            return False

        return False

    def get_stats(self) -> Dict:
        """Get order routing statistics."""
        return {
            "total_orders": self.order_count,
            "rejects": self.reject_count,
            "reject_rate": self.reject_count / max(self.order_count, 1),
            "kill_switch_active": self.risk_engine.risk_monitor.kill_switch_active,
            "kill_reason": self.risk_engine.risk_monitor.kill_reason,
            "capital": self._capital,
            "audit_entries": len(self.audit_log),
            "reliability": self.reliability_monitor.summary(),
            "capacity_curves": {
                "enabled": bool(self.capacity_model.enabled),
                "storage_path": str(self.capacity_model.storage_path),
            },
            "live_ops_controls": {
                "idempotency_ttl_seconds": float(self.idempotency_guard.ttl_seconds),
                "require_live_client_order_id": bool(self.require_live_client_order_id),
                "idempotency_rejects": int(self._live_idempotency_rejects),
                "rate_limit_rejects": int(self._live_rate_limit_rejects),
                "rate_limit_denials_by_endpoint": dict(self._rate_limit_denials),
            },
        }

    def run_weekly_tca_calibration(
        self,
        eta_by_symbol_venue: Dict[Tuple[str, str], float],
        min_samples: int = 50,
        alert_threshold_pct: float = 20.0,
        lookback_days: int = 30,
    ) -> Tuple[Dict[Tuple[str, str], float], List[Dict]]:
        """Update eta parameters by symbol/venue from realized TCA outcomes."""
        updated, analyses = weekly_calibrate_eta(
            tca_db=self.tca_db,
            current_eta_by_market=eta_by_symbol_venue,
            min_samples=min_samples,
            alert_threshold_pct=alert_threshold_pct,
            days=lookback_days,
        )
        self.eta_by_symbol_venue = updated

        if updated:
            self.cost_model.eta = sum(updated.values()) / len(updated)

        return updated, analyses

    def evaluate_paper_live_readiness(
        self,
        *,
        lookback_days: int = 60,
        min_days_required: int = 30,
        min_fills_required: int = 200,
        max_p95_slippage_bps: float = 20.0,
        max_mape_pct: float = 35.0,
    ) -> Dict[str, Any]:
        evaluator = PaperTrackRecordEvaluator(self.tca_db)
        result = evaluator.evaluate(
            lookback_days=lookback_days,
            min_days_required=min_days_required,
            min_fills_required=min_fills_required,
            max_p95_slippage_bps=max_p95_slippage_bps,
            max_mape_pct=max_mape_pct,
        )
        return result.to_dict()

    def get_audit_log(self, n: int = 100) -> List[Dict]:
        """Get recent audit log entries."""
        return self.audit_log[-n:]

    async def reset_risk(self):
        """Reset risk engine (requires manual review)."""
        self.risk_engine.reset()
        logger.info("Risk engine reset - trading resumed")

    def force_halt(self, reason: str) -> RiskState:
        """
        Manually halt order admission without flattening.

        Used by external operational controls such as reconciliation daemons
        when venue/internal state diverges.
        """
        state = self.risk_engine.manual_halt(reason)
        self.audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "control": "manual_halt",
                "reason": str(reason),
                "decision": state.decision.value,
            }
        )
        logger.critical("Manual HALT engaged by external control: %s", reason)
        return state
