"""Point-in-time prediction-market microstructure features for alpha research."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd


def _coerce_timestamp(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_float(value: Any, default: float = math.nan) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _quote_is_valid(bid: float, ask: float) -> bool:
    return math.isfinite(bid) and math.isfinite(ask) and 0.0 <= bid <= ask <= 1.0


@dataclass(frozen=True)
class PredictionMarketBookSnapshot:
    """One as-of market snapshot for a binary prediction-market outcome."""

    market_id: str
    outcome_id: str
    timestamp: datetime
    yes_bid: float
    yes_ask: float
    yes_bid_size: float = 0.0
    yes_ask_size: float = 0.0
    no_bid: float = math.nan
    no_ask: float = math.nan
    no_bid_size: float = 0.0
    no_ask_size: float = 0.0
    last_price: float = math.nan
    traded_volume: float = 0.0
    liquidity: float = 0.0
    source: str = "unknown"
    sequence: int = 0
    resolved_probability: float | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PredictionMarketBookSnapshot":
        return cls(
            market_id=str(payload.get("market_id", "")).strip(),
            outcome_id=str(payload.get("outcome_id", "")).strip(),
            timestamp=_coerce_timestamp(payload.get("timestamp", datetime.now(timezone.utc))),
            yes_bid=_safe_float(payload.get("yes_bid")),
            yes_ask=_safe_float(payload.get("yes_ask")),
            yes_bid_size=max(_safe_float(payload.get("yes_bid_size"), 0.0), 0.0),
            yes_ask_size=max(_safe_float(payload.get("yes_ask_size"), 0.0), 0.0),
            no_bid=_safe_float(payload.get("no_bid")),
            no_ask=_safe_float(payload.get("no_ask")),
            no_bid_size=max(_safe_float(payload.get("no_bid_size"), 0.0), 0.0),
            no_ask_size=max(_safe_float(payload.get("no_ask_size"), 0.0), 0.0),
            last_price=_safe_float(payload.get("last_price")),
            traded_volume=max(_safe_float(payload.get("traded_volume"), 0.0), 0.0),
            liquidity=max(_safe_float(payload.get("liquidity"), 0.0), 0.0),
            source=str(payload.get("source", "unknown")).strip() or "unknown",
            sequence=int(payload.get("sequence", 0) or 0),
            resolved_probability=(
                None
                if payload.get("resolved_probability") is None
                else _safe_float(payload.get("resolved_probability"))
            ),
            metadata=dict(payload.get("metadata", {}) or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["timestamp"] = self.timestamp.isoformat()
        return out


def build_prediction_market_microstructure_features(
    snapshots: Iterable[PredictionMarketBookSnapshot | dict[str, Any]],
    *,
    max_staleness_seconds: float = 60.0,
    wide_spread_threshold_bps: float = 750.0,
) -> pd.DataFrame:
    """Build causal feature rows from ordered prediction-market book snapshots.

    Resolution labels are accepted on the input object for audit/research joins,
    but they are deliberately not emitted as feature columns.
    """

    rows: list[dict[str, Any]] = []
    for item in snapshots:
        snap = item if isinstance(item, PredictionMarketBookSnapshot) else PredictionMarketBookSnapshot.from_dict(item)
        yes_valid = _quote_is_valid(snap.yes_bid, snap.yes_ask)
        no_valid = _quote_is_valid(snap.no_bid, snap.no_ask)
        yes_mid = (snap.yes_bid + snap.yes_ask) / 2.0 if yes_valid else snap.last_price
        no_mid = (snap.no_bid + snap.no_ask) / 2.0 if no_valid else math.nan
        yes_spread = snap.yes_ask - snap.yes_bid if yes_valid else math.nan
        spread_bps = yes_spread / yes_mid * 10000.0 if yes_valid and yes_mid > 0.0 else math.nan
        total_yes_size = max(snap.yes_bid_size + snap.yes_ask_size, 1e-9)
        depth_imbalance = (snap.yes_bid_size - snap.yes_ask_size) / total_yes_size
        quality_flags: list[str] = []
        if not yes_valid:
            quality_flags.append("invalid_yes_quote")
        if math.isfinite(snap.no_bid) or math.isfinite(snap.no_ask):
            if not no_valid:
                quality_flags.append("invalid_no_quote")
        if math.isfinite(spread_bps) and spread_bps > wide_spread_threshold_bps:
            quality_flags.append("wide_spread")
        if math.isfinite(yes_mid) and not 0.0 <= yes_mid <= 1.0:
            quality_flags.append("invalid_probability_mid")

        rows.append(
            {
                "market_id": snap.market_id,
                "outcome_id": snap.outcome_id,
                "timestamp": snap.timestamp,
                "source": snap.source,
                "sequence": int(snap.sequence),
                "yes_mid_probability": float(yes_mid),
                "yes_spread": float(yes_spread) if math.isfinite(yes_spread) else math.nan,
                "yes_spread_bps": float(spread_bps) if math.isfinite(spread_bps) else math.nan,
                "no_mid_probability": float(no_mid) if math.isfinite(no_mid) else math.nan,
                "yes_no_parity_gap": (
                    float(yes_mid + no_mid - 1.0)
                    if math.isfinite(yes_mid) and math.isfinite(no_mid)
                    else math.nan
                ),
                "yes_bid_size": float(snap.yes_bid_size),
                "yes_ask_size": float(snap.yes_ask_size),
                "depth_imbalance": float(depth_imbalance),
                "traded_volume": float(snap.traded_volume),
                "liquidity": float(snap.liquidity),
                "liquidity_score": float(math.log1p(snap.liquidity)),
                "quality_flags": tuple(quality_flags),
            }
        )

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows).sort_values(
        ["market_id", "outcome_id", "timestamp", "sequence"]
    )
    grouped = frame.groupby(["market_id", "outcome_id"], sort=False)
    frame["prior_yes_mid_probability"] = grouped["yes_mid_probability"].shift(1)
    frame["yes_mid_delta"] = (
        frame["yes_mid_probability"] - frame["prior_yes_mid_probability"]
    )
    frame["prior_timestamp"] = grouped["timestamp"].shift(1)
    frame["seconds_since_prior"] = (
        frame["timestamp"] - frame["prior_timestamp"]
    ).dt.total_seconds()
    frame["is_stale"] = frame["seconds_since_prior"] > float(max_staleness_seconds)
    frame["volume_delta"] = grouped["traded_volume"].diff()
    frame["non_monotonic_volume"] = frame["volume_delta"] < 0.0
    frame["volume_velocity_per_second"] = (
        frame["volume_delta"].clip(lower=0.0) / frame["seconds_since_prior"]
    ).fillna(0.0)

    flags: list[tuple[str, ...]] = []
    for _, row in frame.iterrows():
        row_flags = list(row["quality_flags"])
        if bool(row["is_stale"]):
            row_flags.append("stale_snapshot")
        if bool(row["non_monotonic_volume"]):
            row_flags.append("non_monotonic_volume")
        flags.append(tuple(sorted(set(row_flags))))
    frame["quality_flags"] = flags

    return frame.reset_index(drop=True)
