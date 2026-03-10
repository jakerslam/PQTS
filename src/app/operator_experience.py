"""Shared operator-experience catalogs and explainers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class StrategyCatalogEntry:
    key: str
    label: str
    audience: str
    markets: tuple[str, ...]
    complexity: str
    summary: str
    why_it_matters: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RiskProfileEntry:
    key: str
    label: str
    audience: str
    max_notional_pct: float
    drawdown_guardrail_pct: float
    summary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


STRATEGY_CATALOG: dict[str, StrategyCatalogEntry] = {
    "market_making": StrategyCatalogEntry(
        key="market_making",
        label="Market Making",
        audience="pro",
        markets=("crypto", "equities", "forex"),
        complexity="advanced",
        summary="Quotes both sides and captures spread with inventory controls.",
        why_it_matters="Core liquidity strategy with strong pro-grade execution diagnostics.",
    ),
    "funding_arbitrage": StrategyCatalogEntry(
        key="funding_arbitrage",
        label="Funding Arbitrage",
        audience="both",
        markets=("crypto",),
        complexity="intermediate",
        summary="Captures positive funding carry with delta-hedged perp/spot structure.",
        why_it_matters="Beginner-readable yield logic with professional cost/risk controls.",
    ),
    "cross_exchange": StrategyCatalogEntry(
        key="cross_exchange",
        label="Cross-Exchange Arbitrage",
        audience="pro",
        markets=("crypto", "forex"),
        complexity="advanced",
        summary="Exploits venue dislocations with multi-leg routing safety checks.",
        why_it_matters="Execution-quality edge where infrastructure quality matters most.",
    ),
    "trend_following": StrategyCatalogEntry(
        key="trend_following",
        label="Trend Following",
        audience="beginner",
        markets=("crypto", "equities", "forex"),
        complexity="foundational",
        summary="Rides directional momentum with clear entries/exits.",
        why_it_matters="Fastest path for beginners to understand signal lifecycle end-to-end.",
    ),
    "mean_reversion": StrategyCatalogEntry(
        key="mean_reversion",
        label="Mean Reversion",
        audience="beginner",
        markets=("crypto", "equities"),
        complexity="foundational",
        summary="Trades deviations from short-horizon equilibrium levels.",
        why_it_matters="Simple intuition + robust paper-stage validation behavior.",
    ),
    "underdog_value": StrategyCatalogEntry(
        key="underdog_value",
        label="Underdog Value",
        audience="both",
        markets=("prediction_markets",),
        complexity="intermediate",
        summary="Buys mispriced underdogs only when EV remains positive after costs.",
        why_it_matters="Clear probabilistic workflow useful for both retail and desk operators.",
    ),
    "short_cycle_binary": StrategyCatalogEntry(
        key="short_cycle_binary",
        label="Short-Cycle Binary",
        audience="pro",
        markets=("prediction_markets", "crypto"),
        complexity="advanced",
        summary="Micro-cycle two-leg opportunities with legging/HFT guardrails.",
        why_it_matters="Bridge between beginner templates and pro short-cycle execution discipline.",
    ),
}


RISK_PROFILE_CATALOG: dict[str, RiskProfileEntry] = {
    "conservative": RiskProfileEntry(
        key="conservative",
        label="Conservative",
        audience="beginner",
        max_notional_pct=0.01,
        drawdown_guardrail_pct=0.05,
        summary="Lowest risk envelope; optimized for learning with limited downside.",
    ),
    "balanced": RiskProfileEntry(
        key="balanced",
        label="Balanced",
        audience="both",
        max_notional_pct=0.02,
        drawdown_guardrail_pct=0.08,
        summary="Default blend of progress velocity and risk control.",
    ),
    "aggressive": RiskProfileEntry(
        key="aggressive",
        label="Aggressive",
        audience="pro",
        max_notional_pct=0.04,
        drawdown_guardrail_pct=0.12,
        summary="Higher exposure for experienced operators under strict monitoring.",
    ),
    "professional": RiskProfileEntry(
        key="professional",
        label="Professional",
        audience="pro",
        max_notional_pct=0.06,
        drawdown_guardrail_pct=0.15,
        summary="Desk-level envelope intended for advanced operators with explicit governance.",
    ),
}


BLOCK_REASON_GUIDE: dict[str, str] = {
    "not_underdog": "Signal was rejected because market-implied probability is not in underdog range.",
    "insufficient_depth": "Signal blocked because orderbook depth is below configured minimum.",
    "liquidity_gate": "Signal blocked by liquidity policy; market quality is not sufficient.",
    "capacity_gate": "Signal blocked by capacity limits to avoid over-allocation.",
    "edge_below_threshold": "Model edge did not exceed minimum threshold after calibration.",
    "net_ev_non_positive": "Expected value after cost assumptions is non-positive.",
    "rolling_edge_disable": "Strategy auto-disabled because rolling realized edge degraded below floor.",
    "orders_per_minute_exceeded": "High-frequency guardrail blocked flow due to order-rate breach.",
    "p95_submit_to_ack_slo_breach": "Execution latency exceeded configured p95 budget.",
    "p99_submit_to_ack_slo_breach": "Execution latency exceeded configured p99 budget.",
    "public_admin_ingress_disallowed": "Security gate requires private control-plane access only.",
}


def list_strategy_catalog() -> list[StrategyCatalogEntry]:
    return [STRATEGY_CATALOG[key] for key in sorted(STRATEGY_CATALOG)]


def explain_strategy(strategy_key: str) -> StrategyCatalogEntry | None:
    return STRATEGY_CATALOG.get(str(strategy_key).strip().lower())


def list_risk_profiles() -> list[RiskProfileEntry]:
    return [RISK_PROFILE_CATALOG[key] for key in sorted(RISK_PROFILE_CATALOG)]


def recommend_risk_profile(*, experience: str, capital_usd: float, automation: str) -> RiskProfileEntry:
    experience = str(experience).strip().lower()
    automation = str(automation).strip().lower()
    capital_usd = float(capital_usd)
    if experience in {"new", "beginner", "casual"}:
        return RISK_PROFILE_CATALOG["conservative"]
    if automation in {"manual", "hybrid"} and capital_usd < 25_000:
        return RISK_PROFILE_CATALOG["balanced"]
    if capital_usd >= 250_000 and automation == "auto":
        return RISK_PROFILE_CATALOG["professional"]
    return RISK_PROFILE_CATALOG["aggressive"]


def explain_block_reason(reason_code: str) -> str:
    key = str(reason_code).strip()
    if key in BLOCK_REASON_GUIDE:
        return BLOCK_REASON_GUIDE[key]
    return (
        "Unknown block reason code. Inspect readiness report + router telemetry for "
        "exact gate payload and threshold."
    )


def latest_paths(globs: Iterable[str], *, root: Path) -> list[Path]:
    candidates: list[Path] = []
    for token in globs:
        candidates.extend(root.glob(token))
    unique = sorted({path.resolve() for path in candidates if path.is_file()})
    unique.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return unique
