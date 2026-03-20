"""Transaction-cost feedback loop for predicted vs. realized execution quality."""

from __future__ import annotations

import csv
import importlib.util
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import numpy as np

from core.hotpath_runtime import append_lines as native_append_lines
from core.hotpath_runtime import encode_csv_line as native_encode_csv_line

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd


logger = logging.getLogger(__name__)

SLIPPAGE_MAPE_DENOM_FLOOR_BPS = 1.0
MIN_CALIBRATED_ETA = 0.005
MAX_CALIBRATED_ETA = 3.0

TCA_CSV_COLUMNS = (
    "trade_id",
    "timestamp",
    "symbol",
    "exchange",
    "side",
    "quantity",
    "price",
    "notional",
    "predicted_slippage_bps",
    "predicted_commission_bps",
    "predicted_total_bps",
    "realized_slippage_bps",
    "realized_commission_bps",
    "realized_total_bps",
    "spread_bps",
    "vol_24h",
    "depth_1pct_usd",
    "strategy_id",
    "expected_alpha_bps",
    "prediction_profile",
    "expected_gross_alpha_usd",
    "realized_commission_cost_usd",
    "realized_slippage_cost_usd",
    "realized_net_alpha_usd",
    "spread_capture_proxy_usd",
    "adverse_selection_proxy_usd",
    "inventory_carry_proxy_usd",
)


def _pd():
    import pandas as pd

    return pd


def _has_pyarrow() -> bool:
    return importlib.util.find_spec("pyarrow") is not None


def slippage_mape_pct(
    *,
    predicted_slippage_bps: np.ndarray | pd.Series | List[float],
    realized_slippage_bps: np.ndarray | pd.Series | List[float],
    denom_floor_bps: float = SLIPPAGE_MAPE_DENOM_FLOOR_BPS,
) -> float:
    """
    Compute robust slippage MAPE in percent.

    Denominator is floored in bps space so near-zero realized slippage does not
    inflate errors into unusable calibration alerts.
    """
    predicted = np.asarray(predicted_slippage_bps, dtype=float)
    realized = np.asarray(realized_slippage_bps, dtype=float)
    if predicted.size == 0 or realized.size == 0:
        return 0.0

    size = min(predicted.size, realized.size)
    predicted = predicted[:size]
    realized = realized[:size]
    denom = np.maximum(np.abs(realized), max(float(denom_floor_bps), 1e-9))
    return float(np.mean(np.abs(predicted - realized) / denom) * 100.0)


@dataclass(frozen=True)
class ExecutionFill:
    """Canonical fill payload for paper/live execution sources."""

    executed_price: float
    executed_qty: float
    timestamp: datetime
    venue: str
    symbol: str


@dataclass
class TCATradeRecord:
    """Single trade with predicted and realized cost components."""

    trade_id: str
    timestamp: datetime
    symbol: str
    exchange: str
    side: str
    quantity: float
    price: float
    notional: float
    predicted_slippage_bps: float
    predicted_commission_bps: float
    predicted_total_bps: float
    realized_slippage_bps: float
    realized_commission_bps: float
    realized_total_bps: float
    spread_bps: float
    vol_24h: float
    depth_1pct_usd: float
    strategy_id: str = "unknown"
    expected_alpha_bps: float = 0.0
    prediction_profile: str = "unknown"
    expected_gross_alpha_usd: float = 0.0
    realized_commission_cost_usd: float = 0.0
    realized_slippage_cost_usd: float = 0.0
    realized_net_alpha_usd: float = 0.0
    spread_capture_proxy_usd: float = 0.0
    adverse_selection_proxy_usd: float = 0.0
    inventory_carry_proxy_usd: float = 0.0

    @property
    def slippage_error(self) -> float:
        return self.predicted_slippage_bps - self.realized_slippage_bps

    @property
    def realized_net_alpha_bps(self) -> float:
        return float(self.expected_alpha_bps) - float(self.realized_total_bps)


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        token = float(value)
        if token > 10_000_000_000:
            token /= 1000.0
        return datetime.fromtimestamp(token, tz=timezone.utc)
    token = str(value).strip()
    if not token:
        return datetime.now(timezone.utc)
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        try:
            parsed = datetime.fromtimestamp(float(token), tz=timezone.utc)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class TCADatabase:
    """Persist TCA records to CSV/Parquet with deterministic load/save behavior."""

    def __init__(self, db_path: str = "data/tca_records.csv"):
        self.db_path = Path(db_path)
        self.storage_path = self._resolve_storage_path()
        self.records: List[TCATradeRecord] = []
        self._saved_record_count = 0
        self._load_existing()

    def _resolve_storage_path(self) -> Path:
        if self.db_path.suffix.lower() == ".csv":
            return self.db_path
        return self.db_path.with_suffix(".csv")

    def _candidate_paths(self) -> List[Path]:
        candidates = [self.storage_path]
        candidates.append(self.storage_path.with_suffix(".parquet"))
        return candidates

    @staticmethod
    def _float_or_default(value: Any, default: float = 0.0) -> float:
        if value is None:
            return float(default)
        try:
            if isinstance(value, float) and np.isnan(value):
                return float(default)
        except TypeError:
            pass
        token = str(value).strip()
        if token == "" or token.lower() == "nan":
            return float(default)
        try:
            return float(token)
        except ValueError:
            return float(default)

    @staticmethod
    def _string_or_default(value: Any, default: str) -> str:
        token = str(value).strip() if value is not None else ""
        return token or str(default)

    def _record_from_mapping(self, payload: Dict[str, Any]) -> TCATradeRecord:
        return TCATradeRecord(
            trade_id=self._string_or_default(payload.get("trade_id"), "unknown_trade"),
            timestamp=_ensure_datetime(payload.get("timestamp")),
            symbol=self._string_or_default(payload.get("symbol"), "unknown_symbol"),
            exchange=self._string_or_default(payload.get("exchange"), "unknown_exchange"),
            side=self._string_or_default(payload.get("side"), "buy"),
            quantity=self._float_or_default(payload.get("quantity"), 0.0),
            price=self._float_or_default(payload.get("price"), 0.0),
            notional=self._float_or_default(payload.get("notional"), 0.0),
            predicted_slippage_bps=self._float_or_default(payload.get("predicted_slippage_bps"), 0.0),
            predicted_commission_bps=self._float_or_default(payload.get("predicted_commission_bps"), 0.0),
            predicted_total_bps=self._float_or_default(payload.get("predicted_total_bps"), 0.0),
            realized_slippage_bps=self._float_or_default(payload.get("realized_slippage_bps"), 0.0),
            realized_commission_bps=self._float_or_default(payload.get("realized_commission_bps"), 0.0),
            realized_total_bps=self._float_or_default(payload.get("realized_total_bps"), 0.0),
            spread_bps=self._float_or_default(payload.get("spread_bps"), 0.0),
            vol_24h=self._float_or_default(payload.get("vol_24h"), 0.0),
            depth_1pct_usd=self._float_or_default(payload.get("depth_1pct_usd"), 0.0),
            strategy_id=self._string_or_default(payload.get("strategy_id"), "unknown"),
            expected_alpha_bps=self._float_or_default(payload.get("expected_alpha_bps"), 0.0),
            prediction_profile=self._string_or_default(payload.get("prediction_profile"), "unknown"),
            expected_gross_alpha_usd=self._float_or_default(payload.get("expected_gross_alpha_usd"), 0.0),
            realized_commission_cost_usd=self._float_or_default(
                payload.get("realized_commission_cost_usd"), 0.0
            ),
            realized_slippage_cost_usd=self._float_or_default(
                payload.get("realized_slippage_cost_usd"), 0.0
            ),
            realized_net_alpha_usd=self._float_or_default(payload.get("realized_net_alpha_usd"), 0.0),
            spread_capture_proxy_usd=self._float_or_default(payload.get("spread_capture_proxy_usd"), 0.0),
            adverse_selection_proxy_usd=self._float_or_default(
                payload.get("adverse_selection_proxy_usd"), 0.0
            ),
            inventory_carry_proxy_usd=self._float_or_default(
                payload.get("inventory_carry_proxy_usd"), 0.0
            ),
        )

    def _load_csv_records(self, path: Path) -> List[TCATradeRecord]:
        rows: List[TCATradeRecord] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(self._record_from_mapping(dict(row)))
        return rows

    def _load_existing(self) -> None:
        for path in self._candidate_paths():
            if not path.exists():
                continue

            try:
                if path.suffix == ".parquet":
                    if not _has_pyarrow():
                        continue
                    pd = _pd()
                    frame = pd.read_parquet(path)
                    loaded = self._df_to_records(frame)
                else:
                    loaded = self._load_csv_records(path)
            except Exception as exc:  # pragma: no cover - IO safety
                logger.warning("Could not load TCA data from %s: %s", path, exc)
                continue

            self.storage_path = self.storage_path.with_suffix(".csv")
            self.records = loaded
            self._saved_record_count = len(self.records)
            logger.info("Loaded %s TCA records from %s", len(self.records), path)
            return

    def _df_to_records(self, frame: pd.DataFrame) -> List[TCATradeRecord]:
        records: List[TCATradeRecord] = []
        for _, row in frame.iterrows():
            records.append(self._record_from_mapping(row.to_dict()))
        return records

    def _records_to_df(self) -> pd.DataFrame:
        pd = _pd()
        rows: List[Dict[str, Any]] = []
        for record in self.records:
            rows.append(
                {
                    "trade_id": record.trade_id,
                    "timestamp": record.timestamp,
                    "symbol": record.symbol,
                    "exchange": record.exchange,
                    "side": record.side,
                    "quantity": float(record.quantity),
                    "price": float(record.price),
                    "notional": float(record.notional),
                    "predicted_slippage_bps": float(record.predicted_slippage_bps),
                    "predicted_commission_bps": float(record.predicted_commission_bps),
                    "predicted_total_bps": float(record.predicted_total_bps),
                    "realized_slippage_bps": float(record.realized_slippage_bps),
                    "realized_commission_bps": float(record.realized_commission_bps),
                    "realized_total_bps": float(record.realized_total_bps),
                    "spread_bps": float(record.spread_bps),
                    "vol_24h": float(record.vol_24h),
                    "depth_1pct_usd": float(record.depth_1pct_usd),
                    "strategy_id": record.strategy_id,
                    "expected_alpha_bps": float(record.expected_alpha_bps),
                    "prediction_profile": record.prediction_profile,
                    "expected_gross_alpha_usd": float(record.expected_gross_alpha_usd),
                    "realized_commission_cost_usd": float(record.realized_commission_cost_usd),
                    "realized_slippage_cost_usd": float(record.realized_slippage_cost_usd),
                    "realized_net_alpha_usd": float(record.realized_net_alpha_usd),
                    "spread_capture_proxy_usd": float(record.spread_capture_proxy_usd),
                    "adverse_selection_proxy_usd": float(record.adverse_selection_proxy_usd),
                    "inventory_carry_proxy_usd": float(record.inventory_carry_proxy_usd),
                }
            )
        return pd.DataFrame(rows, columns=list(TCA_CSV_COLUMNS))

    @staticmethod
    def _record_to_csv_fields(record: TCATradeRecord) -> List[str]:
        return [
            str(record.trade_id),
            _ensure_datetime(record.timestamp).isoformat(),
            str(record.symbol),
            str(record.exchange),
            str(record.side),
            str(float(record.quantity)),
            str(float(record.price)),
            str(float(record.notional)),
            str(float(record.predicted_slippage_bps)),
            str(float(record.predicted_commission_bps)),
            str(float(record.predicted_total_bps)),
            str(float(record.realized_slippage_bps)),
            str(float(record.realized_commission_bps)),
            str(float(record.realized_total_bps)),
            str(float(record.spread_bps)),
            str(float(record.vol_24h)),
            str(float(record.depth_1pct_usd)),
            str(record.strategy_id),
            str(float(record.expected_alpha_bps)),
            str(record.prediction_profile),
            str(float(record.expected_gross_alpha_usd)),
            str(float(record.realized_commission_cost_usd)),
            str(float(record.realized_slippage_cost_usd)),
            str(float(record.realized_net_alpha_usd)),
            str(float(record.spread_capture_proxy_usd)),
            str(float(record.adverse_selection_proxy_usd)),
            str(float(record.inventory_carry_proxy_usd)),
        ]

    def add_record(self, record: TCATradeRecord) -> None:
        self.records.append(record)

    def save(self) -> Path:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        pending = self.records[self._saved_record_count :]
        if not pending:
            return self.storage_path

        lines: List[str] = []
        if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
            lines.append(native_encode_csv_line(TCA_CSV_COLUMNS))
        for record in pending:
            lines.append(native_encode_csv_line(self._record_to_csv_fields(record)))

        native_append_lines(str(self.storage_path), lines)
        self._saved_record_count = len(self.records)

        logger.info("Saved %s TCA records to %s", len(self.records), self.storage_path)
        return self.storage_path

    def as_dataframe(self) -> pd.DataFrame:
        return self._records_to_df()

    def get_recent(self, n: int = 100) -> pd.DataFrame:
        frame = self._records_to_df()
        return frame.tail(n)

    def get_by_symbol(self, symbol: str, days: int = 30) -> pd.DataFrame:
        frame = self._records_to_df()
        if frame.empty:
            return frame
        pd = _pd()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        return frame[(frame["symbol"] == symbol) & (timestamps >= cutoff)]

    def get_by_venue(self, exchange: str, days: int = 30) -> pd.DataFrame:
        frame = self._records_to_df()
        if frame.empty:
            return frame
        pd = _pd()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        return frame[(frame["exchange"] == exchange) & (timestamps >= cutoff)]

    def get_by_symbol_venue(self, symbol: str, exchange: str, days: int = 30) -> pd.DataFrame:
        frame = self._records_to_df()
        if frame.empty:
            return frame
        pd = _pd()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        return frame[
            (frame["symbol"] == symbol) & (frame["exchange"] == exchange) & (timestamps >= cutoff)
        ]


class TCACalibrator:
    """Weekly slippage-calibration routines by symbol/venue."""

    def __init__(
        self,
        tca_db: TCADatabase,
        min_samples: int = 50,
        alert_threshold_pct: float = 20.0,
        adaptation_rate: float = 0.75,
        max_step_pct: float = 0.80,
        prediction_profile: str = "",
    ):
        self.tca_db = tca_db
        self.min_samples = min_samples
        self.alert_threshold_pct = alert_threshold_pct
        self.adaptation_rate = float(np.clip(float(adaptation_rate), 0.0, 1.0))
        self.max_step_pct = float(max(float(max_step_pct), 0.0))
        self.prediction_profile = str(prediction_profile or "").strip()

    def _filter_prediction_profile(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        if not self.prediction_profile:
            return frame
        if "prediction_profile" not in frame.columns:
            return frame.iloc[0:0].copy()
        mask = frame["prediction_profile"].astype(str) == self.prediction_profile
        return frame[mask].copy()

    @staticmethod
    def _apply_lookback(frame: pd.DataFrame, *, days: int) -> pd.DataFrame:
        if frame.empty:
            return frame
        pd = _pd()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        return frame[timestamps >= cutoff]

    def _calibration_frame(
        self,
        *,
        symbol: str,
        exchange: str,
        days: int,
    ) -> Tuple[pd.DataFrame, str]:
        symbol_frame = self.tca_db.get_by_symbol_venue(symbol, exchange, days=days)
        symbol_frame = self._filter_prediction_profile(symbol_frame)
        if len(symbol_frame) >= self.min_samples:
            return symbol_frame, "symbol_venue"

        venue_frame = self.tca_db.get_by_venue(exchange, days=days)
        venue_frame = self._filter_prediction_profile(venue_frame)
        if len(venue_frame) >= self.min_samples:
            return venue_frame, "venue_fallback"

        global_frame = self._apply_lookback(self.tca_db.as_dataframe(), days=days)
        global_frame = self._filter_prediction_profile(global_frame)
        if len(global_frame) >= self.min_samples:
            return global_frame, "global_fallback"

        return symbol_frame, "insufficient_data"

    def analyze_symbol_venue(self, symbol: str, exchange: str, days: int = 30) -> Dict[str, Any]:
        pd = _pd()
        frame = self.tca_db.get_by_symbol_venue(symbol, exchange, days=days)
        if len(frame) < self.min_samples:
            return {
                "symbol": symbol,
                "exchange": exchange,
                "status": "insufficient_data",
                "n_trades": len(frame),
                "needs": self.min_samples,
                "alerts": [],
            }

        predicted = pd.to_numeric(frame["predicted_slippage_bps"], errors="coerce").fillna(0.0)
        realized = pd.to_numeric(frame["realized_slippage_bps"], errors="coerce").fillna(0.0)
        errors = predicted - realized
        mape = slippage_mape_pct(
            predicted_slippage_bps=predicted,
            realized_slippage_bps=realized,
        )

        alerts: List[str] = []
        analysis: Dict[str, Any] = {
            "symbol": symbol,
            "exchange": exchange,
            "status": "ok",
            "n_trades": len(frame),
            "slippage": {
                "predicted_avg": frame["predicted_slippage_bps"].mean(),
                "realized_avg": frame["realized_slippage_bps"].mean(),
                "mean_error": errors.mean(),
                "mape": mape,
            },
            "alerts": alerts,
        }

        if mape > self.alert_threshold_pct:
            analysis["status"] = "alert"
            alerts.append(f"MAPE {mape:.2f}% exceeds threshold {self.alert_threshold_pct:.2f}%")

        return analysis

    def calibrate_eta(
        self, symbol: str, exchange: str, current_eta: float, days: int = 30
    ) -> Tuple[float, Dict[str, Any]]:
        pd = _pd()
        frame, calibration_scope = self._calibration_frame(
            symbol=symbol,
            exchange=exchange,
            days=days,
        )
        if len(frame) < self.min_samples:
            return current_eta, {
                "symbol": symbol,
                "exchange": exchange,
                "status": "insufficient_data",
                "n_trades": len(frame),
                "eta_before": current_eta,
                "eta_after": current_eta,
                "calibration_scope": calibration_scope,
            }

        predicted_avg = float(
            pd.to_numeric(frame["predicted_slippage_bps"], errors="coerce").mean()
        )
        realized_avg = float(pd.to_numeric(frame["realized_slippage_bps"], errors="coerce").mean())

        baseline = max(abs(predicted_avg), float(SLIPPAGE_MAPE_DENOM_FLOOR_BPS))
        ratio = max(realized_avg, 0.0) / baseline
        current_eta_clamped = float(np.clip(current_eta, MIN_CALIBRATED_ETA, MAX_CALIBRATED_ETA))
        target_eta = float(
            np.clip(current_eta_clamped * ratio, MIN_CALIBRATED_ETA, MAX_CALIBRATED_ETA)
        )
        blended_eta = float(
            current_eta_clamped + self.adaptation_rate * (target_eta - current_eta_clamped)
        )

        if self.max_step_pct > 0.0:
            max_delta = abs(current_eta_clamped) * self.max_step_pct
            lower = max(current_eta_clamped - max_delta, MIN_CALIBRATED_ETA)
            upper = min(current_eta_clamped + max_delta, MAX_CALIBRATED_ETA)
            blended_eta = float(np.clip(blended_eta, lower, upper))

        new_eta = float(np.clip(blended_eta, MIN_CALIBRATED_ETA, MAX_CALIBRATED_ETA))

        predicted = pd.to_numeric(frame["predicted_slippage_bps"], errors="coerce").fillna(0.0)
        realized = pd.to_numeric(frame["realized_slippage_bps"], errors="coerce").fillna(0.0)
        errors = predicted - realized
        mape = slippage_mape_pct(
            predicted_slippage_bps=predicted,
            realized_slippage_bps=realized,
        )
        alerts: List[str] = []
        status = "ok"
        if mape > self.alert_threshold_pct:
            status = "alert"
            alerts.append(f"MAPE {mape:.2f}% exceeds threshold {self.alert_threshold_pct:.2f}%")
        analysis: Dict[str, Any] = {
            "symbol": symbol,
            "exchange": exchange,
            "status": status,
            "n_trades": len(frame),
            "slippage": {
                "predicted_avg": float(predicted.mean()),
                "realized_avg": float(realized.mean()),
                "mean_error": float(errors.mean()),
                "mape": float(mape),
            },
            "alerts": alerts,
        }
        analysis.update(
            {
                "eta_before": current_eta,
                "eta_target": target_eta,
                "eta_after": new_eta,
                "change_pct": ((new_eta - current_eta) / max(current_eta, 1e-9)) * 100.0,
                "ratio_realized_to_predicted": ratio,
                "adaptation_rate": float(self.adaptation_rate),
                "max_step_pct": float(self.max_step_pct),
                "calibration_scope": calibration_scope,
                "calibration_samples": int(len(frame)),
            }
        )

        return new_eta, analysis

    def run_weekly_calibration_by_market(
        self,
        current_eta_by_market: Dict[Tuple[str, str], float],
        days: int = 30,
    ) -> Tuple[Dict[Tuple[str, str], float], List[Dict[str, Any]]]:
        updated = current_eta_by_market.copy()
        analyses: List[Dict[str, Any]] = []

        for (symbol, exchange), eta in sorted(current_eta_by_market.items()):
            new_eta, analysis = self.calibrate_eta(symbol, exchange, eta, days=days)
            updated[(symbol, exchange)] = new_eta
            analyses.append(analysis)

        return updated, analyses


def weekly_calibrate_eta(
    tca_db: TCADatabase,
    current_eta_by_market: Dict[Tuple[str, str], float],
    min_samples: int = 50,
    alert_threshold_pct: float = 20.0,
    adaptation_rate: float = 0.75,
    max_step_pct: float = 0.80,
    days: int = 30,
    prediction_profile: str = "",
) -> Tuple[Dict[Tuple[str, str], float], List[Dict[str, Any]]]:
    """Callable weekly calibration entrypoint for schedulers/jobs."""

    calibrator = TCACalibrator(
        tca_db=tca_db,
        min_samples=min_samples,
        alert_threshold_pct=alert_threshold_pct,
        adaptation_rate=adaptation_rate,
        max_step_pct=max_step_pct,
        prediction_profile=prediction_profile,
    )
    return calibrator.run_weekly_calibration_by_market(
        current_eta_by_market=current_eta_by_market,
        days=days,
    )
