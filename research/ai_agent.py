# AI Research Agent - Deterministic Orchestrator
from __future__ import annotations

import hashlib
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from backtesting.purged_cv import BacktestValidator, PurgedKFold
except Exception:  # pragma: no cover - fallback for minimal environments

    class PurgedKFold:  # type: ignore[override]
        def __init__(self, n_splits: int = 5, pct_purge: float = 0.01, pct_embargo: float = 0.01):
            self.n_splits = n_splits
            self.pct_purge = pct_purge
            self.pct_embargo = pct_embargo

        def split(self, X: pd.DataFrame):
            n = len(X)
            fold = max(1, n // max(self.n_splits, 1))
            purge = int(fold * self.pct_purge)
            embargo = int(fold * self.pct_embargo)
            indices = np.arange(n)
            for i in range(self.n_splits):
                test_start = i * fold
                test_end = min((i + 1) * fold, n)
                if test_start >= test_end:
                    continue
                test_idx = indices[test_start:test_end]
                train_left = indices[: max(0, test_start - purge)]
                train_right = indices[min(n, test_end + embargo) :]
                train_idx = np.concatenate([train_left, train_right])
                yield train_idx, test_idx

    class BacktestValidator:  # type: ignore[override]
        def __init__(
            self,
            min_sharpe: float = 0.8,
            min_profit_factor: float = 1.4,
            max_drawdown: float = 0.15,
        ):
            self.min_sharpe = min_sharpe
            self.min_pf = min_profit_factor
            self.max_dd = max_drawdown

        def validate(self, returns: np.ndarray) -> Dict[str, Any]:
            if len(returns) < 10:
                return {"passed": False, "reasons": ["insufficient_returns"], "metrics": {}}
            returns = np.asarray(returns, dtype=float)
            mean = float(np.mean(returns))
            std = float(np.std(returns))
            sharpe = mean / std * np.sqrt(252.0) if std > 0 else 0.0
            gains = float(np.sum(returns[returns > 0]))
            losses = abs(float(np.sum(returns[returns < 0])))
            pf = gains / losses if losses > 0 else 0.0
            curve = np.cumprod(1.0 + returns)
            dd = float(abs(np.min(curve / np.maximum.accumulate(curve) - 1.0)))
            reasons: List[str] = []
            if sharpe < self.min_sharpe:
                reasons.append("low_sharpe")
            if pf < self.min_pf:
                reasons.append("low_profit_factor")
            if dd > self.max_dd:
                reasons.append("high_drawdown")
            return {
                "passed": len(reasons) == 0,
                "reasons": reasons,
                "metrics": {"sharpe": sharpe, "profit_factor": pf, "max_drawdown": dd},
            }


from portfolio.strategy_allocator import StrategyBudgetInput, StrategyCapitalAllocator
from research.auto_generator import AutoStrategyGenerator, StrategyVariant
from research.database import BacktestResult, Experiment, ResearchDatabase
from research.r_analytics_bridge import RAnalyticsBridge
from research.regime_detector import MarketRegime, RegimeDetector
from research.report_builder import ResearchAnalyticsReportBuilder
from research.walk_forward import WalkForwardTester, WalkForwardWindow

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ObjectiveBounds:
    max_sharpe: float
    max_annual_vol: float
    annual_turnover: float
    cost_per_turnover: float

    @property
    def max_net_annual_return(self) -> float:
        gross = self.max_sharpe * self.max_annual_vol
        cost_drag = self.annual_turnover * self.cost_per_turnover
        return gross - cost_drag

    @property
    def max_net_monthly_return(self) -> float:
        return self.max_net_annual_return / 12.0


class _DeterministicVariantStrategy:
    """Walk-forward adapter exposing evaluate(data)->metrics."""

    def __init__(self, agent: "AIResearchAgent", variant: StrategyVariant):
        self._agent = agent
        self._variant = variant

    def evaluate(self, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        metrics = self._agent._run_deterministic_backtest(self._variant, data)
        return {
            "sharpe": metrics["sharpe"],
            "total_return": metrics["total_return"],
            "max_drawdown": metrics["max_drawdown"],
            "total_trades": metrics["total_trades"],
        }


class AIResearchAgent:
    """
    Autonomous research cycle with deterministic scoring and hard promotion gates.

    Pipeline:
    1. Generate strategy variants
    2. Run deterministic cost-aware backtests
    3. Run purged CV + overfit controls
    4. Run walk-forward validation
    5. Promote to paper only when all gates pass
    6. Promote paper -> canary -> live only via persisted stage metrics
    """

    def __init__(self, config: dict):
        self.config = config

        # Subsystems
        self.db = ResearchDatabase(config.get("db_path", "data/research.db"))
        self.generator = AutoStrategyGenerator()
        self.regime_detector = RegimeDetector(config.get("regime", {}))
        self.walk_forward = WalkForwardTester(config.get("walk_forward", {}))
        analytics_cfg = config.get("analytics", {})
        self.report_builder = ResearchAnalyticsReportBuilder(
            output_dir=analytics_cfg.get("report_dir", "data/research_reports"),
            schema_version=analytics_cfg.get("report_schema_version", "1.0.0"),
            db=self.db,
        )

        # Search and promotion controls
        self.search_budget = int(config.get("search_budget", 100))
        self.top_performers = int(config.get("top_performers", 10))
        self.min_sharpe_for_promotion = float(config.get("min_sharpe", 1.0))
        self.max_drawdown = float(config.get("max_drawdown", 0.15))
        self.min_profit_factor = float(config.get("min_profit_factor", 1.25))
        self.max_pbo = float(config.get("max_pbo", 0.4))
        self.min_deflated_sharpe = float(config.get("min_deflated_sharpe", 0.8))
        self.min_walk_forward_consistency = float(config.get("min_walk_forward_consistency", 0.4))

        # Optional R analytics validator
        r_cfg = config.get("r_analytics", {})
        self.r_analytics_enabled = bool(r_cfg.get("enabled", False))
        self.r_analytics_required = bool(r_cfg.get("required", False))
        self.r_min_cv_sharpe = float(r_cfg.get("min_cv_sharpe", self.min_sharpe_for_promotion))
        self.r_bridge = (
            RAnalyticsBridge(
                script_path=str(r_cfg.get("validator_script", "scripts/r/validate_experiment.R")),
                rscript_bin=str(r_cfg.get("rscript_bin", "Rscript")),
                timeout_seconds=float(r_cfg.get("timeout_seconds", 30.0)),
                bootstrap_samples=int(r_cfg.get("bootstrap_samples", 2000)),
            )
            if self.r_analytics_enabled
            else None
        )

        # CV controls
        self.cv_splits = int(config.get("cv_splits", 5))
        self.cv_pct_purge = float(config.get("cv_pct_purge", 0.01))
        self.cv_pct_embargo = float(config.get("cv_pct_embargo", 0.01))

        # Cost model controls
        costs_cfg = config.get("costs", {})
        self.commission_bps = float(costs_cfg.get("commission_bps", 6.0))
        self.slippage_bps = float(costs_cfg.get("slippage_bps", 8.0))
        self.borrow_funding_bps = float(costs_cfg.get("borrow_funding_bps", 4.0))

        # Capacity model controls (capital must be injected from config)
        capacity_cfg = config.get("capacity", {})
        self.deployable_capital = float(
            capacity_cfg.get(
                "deployable_capital",
                config.get(
                    "deployable_capital", config.get("risk", {}).get("initial_capital", 0.0)
                ),
            )
        )
        self.max_annual_turnover_notional = float(
            capacity_cfg.get("max_annual_turnover_notional", max(self.deployable_capital, 0.0))
        )
        allocation_cfg = config.get("allocation", {})
        self.strategy_allocator = StrategyCapitalAllocator(
            max_weight=float(allocation_cfg.get("max_weight", 0.35)),
            min_weight=float(allocation_cfg.get("min_weight", 0.0)),
            capacity_haircut=float(allocation_cfg.get("capacity_haircut", 0.05)),
        )
        self.last_allocation_weights: Dict[str, float] = {}

        # Stage gates
        self.stage_gates = {
            "live_canary": {
                "source_stage": "paper",
                "min_days": int(config.get("paper_min_days", 30)),
                "min_avg_sharpe": self.min_sharpe_for_promotion,
                "max_avg_drawdown": self.max_drawdown,
                "max_slippage_mape": float(config.get("paper_max_slippage_mape", 25.0)),
                "max_kill_switch_triggers": int(config.get("paper_max_kill_switch_triggers", 0)),
            },
            "live": {
                "source_stage": "live_canary",
                "min_days": int(config.get("canary_min_days", 14)),
                "min_avg_sharpe": float(config.get("live_min_sharpe", 0.8)),
                "max_avg_drawdown": float(config.get("live_max_drawdown", 0.12)),
                "max_slippage_mape": float(config.get("live_max_slippage_mape", 20.0)),
                "max_kill_switch_triggers": int(config.get("live_max_kill_switch_triggers", 0)),
            },
        }
        self.live_allowed_strategy_types = {
            str(name).strip().lower()
            for name in config.get(
                "live_allowed_strategy_types", ["market_making", "funding_arbitrage"]
            )
            if str(name).strip()
        }

        # Agent objective constraints
        objective_cfg = config.get("objective", {})
        self.objective_bounds = ObjectiveBounds(
            max_sharpe=float(objective_cfg.get("max_sharpe", 1.5)),
            max_annual_vol=float(objective_cfg.get("max_annual_vol", 0.25)),
            annual_turnover=float(objective_cfg.get("annual_turnover", 6.0)),
            cost_per_turnover=float(objective_cfg.get("cost_per_turnover", 0.0045)),
        )

        # State
        self.active_strategies: Dict[str, Dict] = {}
        self.paper_trading: List[str] = []
        self.live_canary: List[str] = []
        self.live_trading: List[str] = []

        logger.info("AIResearchAgent initialized: budget=%s", self.search_budget)

    # =========================================================================
    # Main Cycle
    # =========================================================================

    def research_cycle(
        self,
        historical_data: Dict[str, pd.DataFrame],
        strategy_types: Optional[List[str]] = None,
    ) -> Dict:
        """
        Main research loop: generate -> test -> rank -> walk-forward -> promote.
        """
        self._validate_historical_data(historical_data)
        if strategy_types is None:
            strategy_types = ["market_making", "cross_exchange", "stat_arb"]

        objective_assessment = self.validate_objective_constraints(self.config.get("objective", {}))
        if not objective_assessment["objective_valid"]:
            logger.warning("Objective constraints failed: %s", objective_assessment["violations"])

        logger.info("Starting research cycle for: %s", strategy_types)
        candidates = self._generate_candidates(strategy_types)
        results = self._run_backtests(candidates, historical_data)
        ranked = self._rank_strategies(results)
        validated = self._walk_forward_test(ranked[: min(20, len(ranked))], historical_data)
        promoted = self._promote_to_paper(validated)
        strategy_reports = self._build_strategy_reports(
            historical_data=historical_data,
            results=results,
            promoted_ids=promoted,
            objective_assessment=objective_assessment,
        )
        report = self._generate_report(
            candidates=candidates,
            results=results,
            validated=validated,
            promoted=promoted,
            objective_assessment=objective_assessment,
            strategy_reports=strategy_reports,
        )

        logger.info(
            "Research cycle complete: %s generated, %s promoted",
            len(candidates),
            len(promoted),
        )
        return report

    def _validate_historical_data(self, data: Dict[str, pd.DataFrame]) -> None:
        if not data:
            raise ValueError("Historical data is required.")
        for symbol, frame in data.items():
            if frame.empty:
                raise ValueError(f"Historical data for {symbol} is empty.")
            if "close" not in frame.columns:
                raise ValueError(f"Historical data for {symbol} must include a 'close' column.")
            if not isinstance(frame.index, pd.DatetimeIndex):
                raise ValueError(f"Historical data for {symbol} must use DatetimeIndex.")

    # =========================================================================
    # Candidate Generation
    # =========================================================================

    def _generate_candidates(
        self,
        strategy_types: List[str],
        variants_per_type: int = 10,
    ) -> List[StrategyVariant]:
        candidates: List[StrategyVariant] = []
        for strategy_type in strategy_types:
            variants = self.generator.generate_strategy_variants(
                strategy_type=strategy_type,
                n_per_feature_set=variants_per_type,
            )
            candidates.extend(variants)

        candidates = sorted(candidates, key=lambda v: v.strategy_id)[: self.search_budget]
        logger.info("Generated %s candidate strategies", len(candidates))
        return candidates

    # =========================================================================
    # Backtesting + CV + Overfit Controls
    # =========================================================================

    def _run_backtests(
        self,
        candidates: List[StrategyVariant],
        data: Dict[str, pd.DataFrame],
    ) -> List[Dict]:
        results: List[Dict] = []

        for variant in candidates:
            experiment = Experiment(
                experiment_id=variant.strategy_id,
                strategy_name=variant.strategy_type,
                variant_id=variant.strategy_id.split("_")[-1],
                features=variant.features,
                parameters=variant.parameters,
                status="backtest",
            )
            self.db.log_experiment(experiment)

            metrics = self._run_deterministic_backtest(variant, data)
            cv_stats = self._run_purged_cv(variant, data)
            deflated_sharpe = self._deflated_sharpe(
                sharpe=float(cv_stats["cv_sharpe"]),
                n_trials=max(len(candidates), 1),
            )
            r_analytics = self._run_r_cv_validation(
                cv_stats=cv_stats,
                n_trials=max(len(candidates), 1),
            )
            r_validator_passed = self._r_validator_gate_pass(r_analytics)

            fitness = self._compute_fitness(
                metrics=metrics,
                cv_stats=cv_stats,
                deflated_sharpe=deflated_sharpe,
            )

            backtest_result = BacktestResult(
                strategy_id=variant.strategy_id,
                features_used=variant.features,
                hyperparameters=variant.parameters,
                pnl=float(metrics["total_return"]),
                sharpe=float(metrics["sharpe"]),
                drawdown=float(metrics["max_drawdown"]),
                win_rate=float(metrics["win_rate"]),
                total_trades=int(metrics["total_trades"]),
                market_regime=metrics.get("market_regime", "unknown"),
                timestamp=datetime.now(),
            )
            self.db.log_backtest_result(backtest_result)

            results.append(
                {
                    "variant": variant,
                    "metrics": metrics,
                    "cv": cv_stats,
                    "deflated_sharpe": deflated_sharpe,
                    "pbo_estimate": cv_stats["pbo_estimate"],
                    "validator_passed": cv_stats["validator_passed"],
                    "validator_reasons": cv_stats["validator_reasons"],
                    "r_analytics": r_analytics,
                    "r_validator_passed": r_validator_passed,
                    "fitness": fitness,
                }
            )

        return results

    def _run_deterministic_backtest(
        self,
        variant: StrategyVariant,
        data: Dict[str, pd.DataFrame],
    ) -> Dict[str, Any]:
        returns = self._aggregate_market_returns(data)
        signal = self._build_variant_signal(variant, returns)
        position = signal.clip(-1.0, 1.0)
        turnover = position.diff().abs().fillna(0.0)

        cost_per_turnover = (
            self.commission_bps + self.slippage_bps + self.borrow_funding_bps
        ) / 10000.0
        pnl_series = position.shift(1).fillna(0.0) * returns - turnover * cost_per_turnover
        pnl_series = pnl_series.replace([np.inf, -np.inf], 0.0).fillna(0.0)

        equity = (1.0 + pnl_series).cumprod()
        if equity.empty:
            equity = pd.Series([1.0], dtype=float)

        total_return = float(equity.iloc[-1] - 1.0)
        pnl_std = float(pnl_series.std(ddof=0))
        periods_per_year = self._periods_per_year(returns.index)
        sharpe = float(
            (pnl_series.mean() / pnl_std) * np.sqrt(periods_per_year) if pnl_std > 0 else 0.0
        )

        running_max = equity.cummax()
        drawdown = (equity / running_max) - 1.0
        max_drawdown = float(abs(drawdown.min())) if not drawdown.empty else 0.0

        traded_mask = turnover > 1e-8
        trade_pnls = pnl_series[traded_mask]
        win_rate = float((trade_pnls > 0).mean()) if len(trade_pnls) else 0.0
        total_trades = int(traded_mask.sum())

        annualized_turnover = float(turnover.sum()) * (periods_per_year / max(len(turnover), 1))
        annual_turnover_notional = annualized_turnover * max(self.deployable_capital, 0.0)
        capacity_ratio = (
            annual_turnover_notional / self.max_annual_turnover_notional
            if self.max_annual_turnover_notional > 0
            else float("inf")
        )
        annual_return_estimate = float(pnl_series.mean()) * periods_per_year

        return {
            "sharpe": sharpe,
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "turnover_annualized": annualized_turnover,
            "annual_return_estimate": annual_return_estimate,
            "cost_drag_bps": float(turnover.sum() * cost_per_turnover * 10000.0),
            "capacity_ratio": float(capacity_ratio),
            "returns_series": pnl_series,
        }

    def _run_purged_cv(
        self, variant: StrategyVariant, data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        returns = self._aggregate_market_returns(data)
        if len(returns) < 40:
            fallback = self._run_deterministic_backtest(variant, data)
            return {
                "cv_sharpe": float(fallback["sharpe"]),
                "cv_sharpe_std": 0.0,
                "cv_drawdown": float(fallback["max_drawdown"]),
                "validator_passed": False,
                "validator_reasons": ["Insufficient samples for purged CV"],
                "pbo_estimate": 1.0,
                "cv_fold_sharpes": [float(fallback["sharpe"])],
            }

        n_splits = max(2, min(self.cv_splits, len(returns) // 20))
        cv = PurgedKFold(
            n_splits=n_splits,
            pct_purge=self.cv_pct_purge,
            pct_embargo=self.cv_pct_embargo,
        )

        cv_sharpes: List[float] = []
        cv_drawdowns: List[float] = []
        oos_returns: List[np.ndarray] = []
        frame = pd.DataFrame({"returns": returns}, index=returns.index)

        for _train_idx, test_idx in cv.split(frame):
            if len(test_idx) < 5:
                continue
            subset = self._slice_data_by_timestamps(data, frame.index[test_idx])
            metrics = self._run_deterministic_backtest(variant, subset)
            cv_sharpes.append(float(metrics["sharpe"]))
            cv_drawdowns.append(float(metrics["max_drawdown"]))
            oos_returns.append(metrics["returns_series"].to_numpy())

        if not cv_sharpes:
            return {
                "cv_sharpe": 0.0,
                "cv_sharpe_std": 0.0,
                "cv_drawdown": 1.0,
                "validator_passed": False,
                "validator_reasons": ["Purged CV produced no valid folds"],
                "pbo_estimate": 1.0,
                "cv_fold_sharpes": [],
            }

        merged_oos_returns = (
            np.concatenate(oos_returns) if oos_returns else np.array([], dtype=float)
        )
        validator = BacktestValidator(
            min_sharpe=self.min_sharpe_for_promotion,
            min_profit_factor=self.min_profit_factor,
            max_drawdown=self.max_drawdown,
        )
        validation = validator.validate(merged_oos_returns)
        pbo_estimate = float(np.mean(np.array(cv_sharpes) <= 0.0))

        return {
            "cv_sharpe": float(np.mean(cv_sharpes)),
            "cv_sharpe_std": float(np.std(cv_sharpes)),
            "cv_drawdown": float(np.mean(cv_drawdowns)),
            "validator_passed": bool(validation["passed"]),
            "validator_reasons": list(validation["reasons"]),
            "pbo_estimate": pbo_estimate,
            "cv_fold_sharpes": [float(value) for value in cv_sharpes],
        }

    def _run_r_cv_validation(self, *, cv_stats: Dict[str, Any], n_trials: int) -> Dict[str, Any]:
        if not self.r_analytics_enabled:
            return {
                "status": "disabled",
                "validator_passed_r": True,
                "reasons": [],
            }

        fold_sharpes = [float(value) for value in cv_stats.get("cv_fold_sharpes", [])]
        if not fold_sharpes:
            message = "No CV fold sharpe values available for R validation."
            if self.r_analytics_required:
                raise RuntimeError(message)
            logger.warning(message)
            return {
                "status": "unavailable",
                "validator_passed_r": True,
                "reasons": [message],
            }

        if self.r_bridge is None:
            message = "R analytics bridge is not configured."
            if self.r_analytics_required:
                raise RuntimeError(message)
            logger.warning(message)
            return {
                "status": "unavailable",
                "validator_passed_r": True,
                "reasons": [message],
            }

        try:
            result = self.r_bridge.run_cv_validation(
                cv_sharpes=fold_sharpes,
                n_trials=n_trials,
                min_deflated_sharpe=self.min_deflated_sharpe,
                max_pbo=self.max_pbo,
                min_cv_sharpe=self.r_min_cv_sharpe,
            )
            return result
        except Exception as exc:
            if self.r_analytics_required:
                raise RuntimeError(f"Required R analytics validation failed: {exc}") from exc
            logger.warning("Optional R analytics validation failed: %s", exc)
            return {
                "status": "error",
                "validator_passed_r": True,
                "reasons": [str(exc)],
            }

    def _r_validator_gate_pass(self, payload: Dict[str, Any]) -> bool:
        if not self.r_analytics_enabled:
            return True
        if not isinstance(payload, dict):
            return not self.r_analytics_required
        if str(payload.get("status", "")).lower() != "ok":
            return not self.r_analytics_required
        return bool(payload.get("validator_passed_r", False))

    def _deflated_sharpe(self, sharpe: float, n_trials: int) -> float:
        if n_trials <= 1:
            return float(sharpe)
        penalty = np.sqrt(2.0 * np.log(float(n_trials))) / np.sqrt(252.0)
        return float(sharpe - penalty)

    def _compute_fitness(
        self, metrics: Dict[str, Any], cv_stats: Dict[str, Any], deflated_sharpe: float
    ) -> float:
        capacity_penalty = max(float(metrics["capacity_ratio"]) - 1.0, 0.0)
        drawdown_penalty = float(metrics["max_drawdown"])
        pbo_penalty = float(cv_stats["pbo_estimate"])
        return float(
            (1.2 * deflated_sharpe)
            + (0.5 * float(metrics["total_return"]))
            + (0.4 * float(cv_stats["cv_sharpe"]))
            - (0.8 * drawdown_penalty)
            - (0.6 * pbo_penalty)
            - (0.5 * capacity_penalty)
        )

    # =========================================================================
    # Walk-Forward + Promotion
    # =========================================================================

    def _rank_strategies(self, results: List[Dict]) -> List[Dict]:
        return sorted(results, key=lambda row: row["fitness"], reverse=True)

    def _walk_forward_test(
        self, top_strategies: List[Dict], data: Dict[str, pd.DataFrame]
    ) -> List[Dict]:
        confirmed: List[Dict] = []
        windows = self._build_walk_forward_windows(data)

        for strategy_data in top_strategies:
            variant = strategy_data["variant"]
            strategy_factory = lambda v=variant: _DeterministicVariantStrategy(self, v)
            wf_result = self.walk_forward.run_walk_forward(strategy_factory, data, windows)
            aggregate = wf_result.get("aggregate", {})

            wf_sharpe = float(aggregate.get("avg_sharpe", 0.0))
            wf_drawdown = float(abs(aggregate.get("avg_drawdown", 1.0)))
            wf_consistency = float(aggregate.get("consistency_score", 0.0))

            strategy_data["walk_forward"] = wf_result
            strategy_data["walk_forward_sharpe"] = wf_sharpe
            strategy_data["walk_forward_drawdown"] = wf_drawdown
            strategy_data["walk_forward_consistency"] = wf_consistency

            passed = (
                wf_sharpe >= self.min_sharpe_for_promotion
                and wf_drawdown <= self.max_drawdown
                and wf_consistency >= self.min_walk_forward_consistency
            )
            strategy_data["walk_forward_passed"] = passed

            if passed:
                confirmed.append(strategy_data)

        logger.info("Walk-forward validated: %s/%s", len(confirmed), len(top_strategies))
        return confirmed

    def _build_walk_forward_windows(self, data: Dict[str, pd.DataFrame]) -> List[WalkForwardWindow]:
        primary_index = self._primary_index(data)
        start = primary_index.min().to_pydatetime()
        end = primary_index.max().to_pydatetime()
        windows = self.walk_forward.generate_windows(start, end)

        if windows:
            return windows

        span = end - start
        if span <= timedelta(days=2):
            return [
                WalkForwardWindow(
                    train_start=start,
                    train_end=end,
                    validation_start=end,
                    validation_end=end,
                    test_start=end,
                    test_end=end,
                )
            ]

        train_end = start + timedelta(seconds=span.total_seconds() * 0.6)
        val_end = start + timedelta(seconds=span.total_seconds() * 0.8)
        return [
            WalkForwardWindow(
                train_start=start,
                train_end=train_end,
                validation_start=train_end,
                validation_end=val_end,
                test_start=val_end,
                test_end=end,
            )
        ]

    def _promote_to_paper(self, validated: List[Dict]) -> List[str]:
        promoted: List[str] = []
        candidates: List[Dict[str, Any]] = []
        cost_per_turnover = (
            self.commission_bps + self.slippage_bps + self.borrow_funding_bps
        ) / 10000.0

        for result in validated:
            variant = result["variant"]
            metrics = result["metrics"]
            annual_return_estimate = float(
                metrics.get("annual_return_estimate", metrics.get("total_return", 0.0))
            )
            annual_turnover = float(metrics.get("turnover_annualized", 0.0))
            net_expected_return = annual_return_estimate - (annual_turnover * cost_per_turnover)

            gates = {
                "validator": bool(result["validator_passed"]),
                "drawdown": float(metrics["max_drawdown"]) <= self.max_drawdown,
                "wf_sharpe": float(result["walk_forward_sharpe"]) >= self.min_sharpe_for_promotion,
                "wf_consistency": float(result["walk_forward_consistency"])
                >= self.min_walk_forward_consistency,
                "deflated_sharpe": float(result["deflated_sharpe"]) >= self.min_deflated_sharpe,
                "pbo": float(result["pbo_estimate"]) <= self.max_pbo,
                "capacity": float(metrics["capacity_ratio"]) <= 1.0,
                "economics": net_expected_return > 0.0,
                "r_validator": bool(
                    result.get(
                        "r_validator_passed",
                        self._r_validator_gate_pass(result.get("r_analytics", {})),
                    )
                ),
            }
            result["net_expected_return"] = net_expected_return
            result["promotion_gates"] = gates

            if not all(gates.values()):
                continue
            candidates.append(result)

        selected = candidates[: self.top_performers]
        allocation_inputs = [
            StrategyBudgetInput(
                strategy_id=row["variant"].strategy_id,
                expected_return=float(row.get("net_expected_return", 0.0)),
                annual_vol=max(
                    float(row["metrics"].get("annual_return_estimate", 0.0))
                    / max(float(row["metrics"].get("sharpe", 0.0)), 0.05),
                    0.01,
                ),
                annual_turnover=float(row["metrics"].get("turnover_annualized", 0.0)),
                cost_per_turnover=cost_per_turnover,
                capacity_ratio=float(row["metrics"].get("capacity_ratio", 0.0)),
            )
            for row in selected
        ]
        allocation_weights = self.strategy_allocator.allocate(allocation_inputs)
        self.last_allocation_weights = dict(allocation_weights)

        for result in selected:
            variant = result["variant"]
            gates = result.get("promotion_gates", {})
            arm = self.db.assign_pilot_arm(variant.strategy_id)
            target_weight = float(allocation_weights.get(variant.strategy_id, 0.0))
            self.db.update_experiment_status(
                variant.strategy_id,
                "paper",
                reason="passed_research_gate",
            )
            self.db.log_stage_metric(
                variant.strategy_id,
                "paper",
                {
                    "pnl": float(result["metrics"]["total_return"]),
                    "sharpe": float(result["walk_forward_sharpe"]),
                    "drawdown": float(result["walk_forward_drawdown"]),
                    "slippage_mape": 0.0,
                    "kill_switch_triggers": 0,
                    "notes": {
                        "gates": gates,
                        "r_analytics": result.get("r_analytics", {}),
                        "arm": arm,
                        "target_weight": target_weight,
                        "net_expected_return": float(result.get("net_expected_return", 0.0)),
                    },
                },
            )

            if variant.strategy_id not in self.paper_trading:
                self.paper_trading.append(variant.strategy_id)
            promoted.append(variant.strategy_id)
            logger.info(
                "Promoted %s to paper trading (arm=%s weight=%.3f)",
                variant.strategy_id,
                arm,
                target_weight,
            )

        return promoted

    # =========================================================================
    # Stage Promotion Gates
    # =========================================================================

    def record_stage_metrics(
        self,
        strategy_id: str,
        stage: str,
        metrics: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> bool:
        return self.db.log_stage_metric(strategy_id, stage, metrics, timestamp=timestamp)

    def evaluate_stage_gate(self, strategy_id: str, target_stage: str) -> Dict[str, Any]:
        if target_stage not in self.stage_gates:
            raise ValueError(f"Unknown target stage: {target_stage}")

        gate = self.stage_gates[target_stage]
        source_stage = gate["source_stage"]
        summary = self.db.get_stage_summary(strategy_id, source_stage, lookback_days=365)

        checks = {
            "days": summary["days"] >= gate["min_days"],
            "sharpe": summary["avg_sharpe"] >= gate["min_avg_sharpe"],
            "drawdown": summary["avg_drawdown"] <= gate["max_avg_drawdown"],
            "slippage_mape": summary["avg_slippage_mape"] <= gate["max_slippage_mape"],
            "kill_switches": summary["total_kill_switch_triggers"]
            <= gate["max_kill_switch_triggers"],
        }
        return {
            "strategy_id": strategy_id,
            "target_stage": target_stage,
            "source_stage": source_stage,
            "summary": summary,
            "checks": checks,
            "passed": all(checks.values()),
        }

    def promote_from_stage(self, strategy_id: str, target_stage: str) -> bool:
        if target_stage in {"live_canary", "live"}:
            experiment = self.db.get_experiment(strategy_id)
            strategy_type = str((experiment or {}).get("strategy_name", "")).strip().lower()
            if strategy_type and strategy_type not in self.live_allowed_strategy_types:
                logger.warning(
                    "Promotion blocked for %s -> %s: strategy type '%s' outside live scope %s",
                    strategy_id,
                    target_stage,
                    strategy_type,
                    sorted(self.live_allowed_strategy_types),
                )
                return False

        assessment = self.evaluate_stage_gate(strategy_id, target_stage)
        if not assessment["passed"]:
            logger.warning(
                "Promotion blocked for %s -> %s: %s",
                strategy_id,
                target_stage,
                assessment["checks"],
            )
            return False

        updated = self.db.update_experiment_status(
            strategy_id,
            target_stage,
            reason=f"passed_{assessment['source_stage']}_gate",
        )
        if not updated:
            return False

        if target_stage == "live_canary" and strategy_id not in self.live_canary:
            self.live_canary.append(strategy_id)
        if target_stage == "live" and strategy_id not in self.live_trading:
            self.live_trading.append(strategy_id)
        return True

    # =========================================================================
    # Reporting + Monitoring
    # =========================================================================

    def _generate_report(
        self,
        candidates: List[StrategyVariant],
        results: List[Dict],
        validated: List[Dict],
        promoted: List[str],
        objective_assessment: Dict[str, Any],
        strategy_reports: Dict[str, Any],
    ) -> Dict:
        sharpes = [row["metrics"]["sharpe"] for row in results]
        returns = [row["metrics"]["total_return"] for row in results]

        top_ranked = sorted(results, key=lambda row: row["fitness"], reverse=True)[:5]
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "candidates_generated": len(candidates),
                "backtests_run": len(results),
                "walk_forward_passed": len(validated),
                "promoted_to_paper": len(promoted),
                "promoted_ids": promoted,
                "allocation_weights": self.last_allocation_weights,
            },
            "objective": objective_assessment,
            "performance": {
                "avg_sharpe": float(np.mean(sharpes)) if sharpes else 0.0,
                "best_sharpe": float(np.max(sharpes)) if sharpes else 0.0,
                "avg_return": float(np.mean(returns)) if returns else 0.0,
                "best_return": float(np.max(returns)) if returns else 0.0,
            },
            "analytics": strategy_reports,
            "top_strategies": [
                {
                    "id": row["variant"].strategy_id,
                    "type": row["variant"].strategy_type,
                    "fitness": float(row["fitness"]),
                    "sharpe": float(row["metrics"]["sharpe"]),
                    "deflated_sharpe": float(row["deflated_sharpe"]),
                    "pbo_estimate": float(row["pbo_estimate"]),
                    "capacity_ratio": float(row["metrics"]["capacity_ratio"]),
                    "net_expected_return": float(row.get("net_expected_return", 0.0)),
                    "features": row["variant"].features,
                }
                for row in top_ranked
            ],
        }

    def _build_strategy_reports(
        self,
        *,
        historical_data: Dict[str, pd.DataFrame],
        results: List[Dict[str, Any]],
        promoted_ids: List[str],
        objective_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        lineage = self._summarize_data_lineage(historical_data)
        entries: List[Dict[str, Any]] = []
        promoted_set = set(promoted_ids)

        for row in results:
            variant = row["variant"]
            strategy_id = variant.strategy_id
            promoted = strategy_id in promoted_set
            stage = self.db.get_experiment_status(strategy_id) or "backtest"

            gate_checks = {
                "validator": bool(row.get("validator_passed", False)),
                "deflated_sharpe": float(row.get("deflated_sharpe", 0.0))
                >= self.min_deflated_sharpe,
                "pbo": float(row.get("pbo_estimate", 1.0)) <= self.max_pbo,
                "capacity": float(row.get("metrics", {}).get("capacity_ratio", 0.0)) <= 1.0,
                "economics": float(row.get("net_expected_return", 0.0)) > 0.0,
                "r_validator": bool(
                    row.get(
                        "r_validator_passed",
                        self._r_validator_gate_pass(row.get("r_analytics", {})),
                    )
                ),
            }

            if promoted:
                decision_action = "promote_to_paper"
                decision_reason = "passed_research_gate"
            elif not gate_checks["validator"]:
                decision_action = "hold"
                decision_reason = "validator_failed"
            elif not gate_checks["pbo"]:
                decision_action = "hold"
                decision_reason = "overfit_risk_high"
            elif not gate_checks["r_validator"]:
                decision_action = "hold"
                decision_reason = "r_validator_failed"
            elif not gate_checks["capacity"]:
                decision_action = "hold"
                decision_reason = "capacity_limit_exceeded"
            elif not gate_checks["economics"]:
                decision_action = "hold"
                decision_reason = "net_expected_return_non_positive"
            else:
                decision_action = "hold"
                decision_reason = "ranked_below_promotion_cutoff"

            validator_reasons = row.get("validator_reasons", [])
            rationale = (
                decision_reason
                if not validator_reasons
                else f"{decision_reason}: {', '.join(str(r) for r in validator_reasons)}"
            )

            confidence = float(np.clip((float(row.get("fitness", 0.0)) + 2.0) / 4.0, 0.0, 1.0))
            report, path, report_hash = self.report_builder.build_and_save_from_result_row(
                result_row=row,
                data_lineage=lineage,
                objective_assessment=objective_assessment,
                promotion_stage=stage,
                promoted=promoted,
                promotion_reason=decision_reason,
                promotion_gate_checks=gate_checks,
                decision={
                    "action": decision_action,
                    "rationale": rationale,
                    "supporting_card_ids": [],
                    "counterevidence_card_ids": [],
                    "confidence": confidence,
                    "operator": "autopilot",
                },
                tca_snapshot={},
                extras={
                    "fitness": float(row.get("fitness", 0.0)),
                    "r_analytics": row.get("r_analytics", {}),
                },
            )
            entries.append(
                {
                    "experiment_id": report.experiment_id,
                    "report_id": report.report_id,
                    "path": str(path),
                    "sha256": report_hash,
                    "decision": decision_action,
                    "promoted": promoted,
                }
            )

        return {
            "report_schema_version": self.report_builder.schema_version,
            "report_count": len(entries),
            "report_dir": str(self.report_builder.output_dir),
            "reports": entries,
        }

    def get_top_strategies(self, n: int = 10) -> pd.DataFrame:
        return self.db.get_top_experiments(n)

    def monitor_paper_trading(self) -> Dict:
        metrics: Dict[str, Dict[str, Any]] = {}
        for strategy_id in list(self.paper_trading):
            summary = self.db.get_stage_summary(strategy_id, "paper", lookback_days=30)
            active = (
                summary["samples"] > 0
                and summary["avg_sharpe"] >= (self.min_sharpe_for_promotion * 0.5)
                and summary["avg_drawdown"] <= (self.max_drawdown * 1.2)
            )
            if not active:
                self.paper_trading.remove(strategy_id)
                self.db.update_experiment_status(
                    strategy_id, "backtest", reason="paper_monitor_demote"
                )

            metrics[strategy_id] = {
                "status": "active" if active else "demoted",
                "avg_sharpe": summary["avg_sharpe"],
                "avg_drawdown": summary["avg_drawdown"],
                "samples": summary["samples"],
                "days": summary["days"],
            }

        return metrics

    def discover_new_regime_strategies(
        self,
        current_regime: MarketRegime,
        data: Dict[str, pd.DataFrame],
    ) -> List[StrategyVariant]:
        _ = data  # Data retained in signature for future regime-specific scoring.
        optimal = self.regime_detector.get_optimal_strategies(current_regime)
        strategy_type = optimal[0] if optimal else "market_making"
        logger.info(
            "Generating regime-specific strategies for %s: %s", current_regime.value, optimal
        )
        return self.generator.generate_strategy_variants(strategy_type, n_per_feature_set=10)

    # =========================================================================
    # Objective + Feasibility
    # =========================================================================

    def assess_profit_target_feasibility(
        self,
        target_annual_profit: float = 1_000_000.0,
        capital: Optional[float] = None,
    ) -> Dict[str, Any]:
        deployable_capital = float(capital if capital is not None else self.deployable_capital)
        scenarios = [
            ("conservative", 1.0, 0.15),
            ("realistic", 1.25, 0.20),
            ("aggressive", 1.5, 0.25),
        ]

        cost_drag = self.objective_bounds.annual_turnover * self.objective_bounds.cost_per_turnover
        rows = []
        for name, sharpe, vol in scenarios:
            gross_return = sharpe * vol
            net_return = gross_return - cost_drag
            required_capital = (
                (target_annual_profit / net_return) if net_return > 0 else float("inf")
            )
            rows.append(
                {
                    "scenario": name,
                    "sharpe": sharpe,
                    "annual_vol": vol,
                    "gross_return": gross_return,
                    "cost_drag": cost_drag,
                    "net_return": net_return,
                    "required_capital": required_capital,
                    "feasible_with_capital": (
                        deployable_capital >= required_capital
                        if required_capital != float("inf")
                        else False
                    ),
                }
            )

        return {
            "target_annual_profit": float(target_annual_profit),
            "deployable_capital": deployable_capital,
            "scenarios": rows,
        }

    def validate_objective_constraints(self, objective: Dict[str, Any]) -> Dict[str, Any]:
        violations: List[str] = []
        target_monthly_return = objective.get("target_monthly_return")
        if target_monthly_return is not None:
            requested = float(target_monthly_return)
            if requested > self.objective_bounds.max_net_monthly_return:
                violations.append(
                    (
                        f"target_monthly_return={requested:.2%} exceeds feasible bound "
                        f"{self.objective_bounds.max_net_monthly_return:.2%} "
                        "(Sharpe/vol/cost constrained)."
                    )
                )

        target_annual_profit = float(objective.get("target_annual_profit", 1_000_000.0))
        feasibility = self.assess_profit_target_feasibility(
            target_annual_profit=target_annual_profit,
            capital=self.deployable_capital,
        )

        return {
            "objective_valid": len(violations) == 0,
            "violations": violations,
            "bounds": {
                "max_net_annual_return": self.objective_bounds.max_net_annual_return,
                "max_net_monthly_return": self.objective_bounds.max_net_monthly_return,
            },
            "profit_target_feasibility": feasibility,
        }

    # =========================================================================
    # Deterministic Helpers
    # =========================================================================

    def _aggregate_market_returns(self, data: Dict[str, pd.DataFrame]) -> pd.Series:
        aligned: List[pd.Series] = []
        for symbol in sorted(data.keys()):
            frame = data[symbol]
            close = pd.to_numeric(frame["close"], errors="coerce").astype(float)
            returns = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
            returns = returns.clip(-0.2, 0.2)
            aligned.append(returns.rename(symbol))

        merged = pd.concat(aligned, axis=1).sort_index().fillna(0.0)
        return merged.mean(axis=1).astype(float)

    def _build_variant_signal(self, variant: StrategyVariant, returns: pd.Series) -> pd.Series:
        seed = int(hashlib.md5(variant.strategy_id.encode("utf-8")).hexdigest()[:8], 16)
        fast = 3 + (seed % 8)
        slow = fast + 10 + (seed % 16)

        fast_ma = returns.rolling(fast, min_periods=1).mean()
        slow_ma = returns.rolling(slow, min_periods=1).mean()
        trend_component = fast_ma - slow_ma
        reversion_component = -returns.rolling(fast, min_periods=1).mean()

        if variant.strategy_type in {"market_making", "stat_arb"}:
            base = reversion_component
        else:
            base = trend_component

        feature_bias = 1.0 + (0.04 * len(variant.features))
        param_bias = 1.0 + (0.02 * len(variant.parameters))
        scaled = base * feature_bias * param_bias
        return np.tanh(scaled * 120.0).astype(float)

    def _periods_per_year(self, index: pd.DatetimeIndex) -> float:
        if len(index) < 3:
            return 252.0
        deltas = index.to_series().diff().dropna()
        median_delta = deltas.median()
        if pd.isna(median_delta) or median_delta <= pd.Timedelta(0):
            return 252.0
        periods = pd.Timedelta(days=365.25) / median_delta
        return float(np.clip(periods, 12.0, 24.0 * 365.25))

    def _slice_data_by_timestamps(
        self,
        data: Dict[str, pd.DataFrame],
        timestamps: pd.DatetimeIndex,
    ) -> Dict[str, pd.DataFrame]:
        index_set = pd.Index(sorted(set(timestamps)))
        sliced: Dict[str, pd.DataFrame] = {}
        for symbol, frame in data.items():
            subset = frame.loc[frame.index.intersection(index_set)]
            if not subset.empty:
                sliced[symbol] = subset
        return sliced

    def _primary_index(self, data: Dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
        first_symbol = sorted(data.keys())[0]
        return data[first_symbol].index

    def _summarize_data_lineage(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        index = self._primary_index(data)
        config_fingerprint = {
            "search_budget": self.search_budget,
            "top_performers": self.top_performers,
            "min_sharpe": self.min_sharpe_for_promotion,
            "max_drawdown": self.max_drawdown,
            "commission_bps": self.commission_bps,
            "slippage_bps": self.slippage_bps,
            "borrow_funding_bps": self.borrow_funding_bps,
        }
        return {
            "dataset_id": self.config.get("dataset_id", "historical_market_data"),
            "symbols": sorted(list(data.keys())),
            "start": index.min().isoformat(),
            "end": index.max().isoformat(),
            "bars": int(sum(len(df) for df in data.values())),
            "timezone": "UTC",
            "source": self.config.get("data_source", "historical"),
            "code_sha": self._resolve_code_sha(),
            "config_hash": hashlib.sha256(
                str(sorted(config_fingerprint.items())).encode("utf-8")
            ).hexdigest(),
        }

    @staticmethod
    def _resolve_code_sha() -> str:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            return completed.stdout.strip() or "unknown"
        except Exception:
            return "unknown"
