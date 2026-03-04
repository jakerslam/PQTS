"""Revenue diagnostics from TCA records for strategy/venue optimization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

import pandas as pd

from execution.tca_feedback import TCADatabase


def _empty_summary() -> Dict[str, Any]:
    return {
        "trades": 0,
        "notional_usd": 0.0,
        "avg_expected_alpha_bps": 0.0,
        "avg_realized_cost_bps": 0.0,
        "avg_realized_net_alpha_bps": 0.0,
        "estimated_predicted_pnl_usd": 0.0,
        "estimated_realized_pnl_usd": 0.0,
        "slippage_mape_pct": 0.0,
    }


class RevenueDiagnostics:
    """Deterministic rollups of expected edge vs realized execution economics."""

    def __init__(self, tca_db_path: str = "data/tca_records.csv"):
        self.tca_db_path = str(tca_db_path)
        self.tca_db = TCADatabase(self.tca_db_path)

    @staticmethod
    def _normalize_frame(frame: pd.DataFrame, *, lookback_days: int) -> pd.DataFrame:
        if frame.empty:
            return frame
        df = frame.copy()
        if "strategy_id" not in df.columns:
            df["strategy_id"] = "unknown"
        if "expected_alpha_bps" not in df.columns:
            df["expected_alpha_bps"] = 0.0
        df["strategy_id"] = df["strategy_id"].fillna("unknown").astype(str)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df[df["timestamp"].notna()]
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(int(lookback_days), 1))
        df = df[df["timestamp"] >= pd.Timestamp(cutoff)]
        if df.empty:
            return df

        numeric_columns: Iterable[str] = (
            "notional",
            "predicted_total_bps",
            "realized_total_bps",
            "predicted_slippage_bps",
            "realized_slippage_bps",
            "expected_alpha_bps",
        )
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        df["predicted_net_alpha_bps"] = df["expected_alpha_bps"] - df["predicted_total_bps"]
        df["realized_net_alpha_bps"] = df["expected_alpha_bps"] - df["realized_total_bps"]
        df["predicted_pnl_usd"] = df["notional"] * df["predicted_net_alpha_bps"] / 10000.0
        df["realized_pnl_usd"] = df["notional"] * df["realized_net_alpha_bps"] / 10000.0
        denom = df["realized_slippage_bps"].abs().replace(0.0, 1e-6)
        df["slippage_ape_pct"] = (
            (df["predicted_slippage_bps"] - df["realized_slippage_bps"]).abs() / denom
        ) * 100.0
        return df

    def _frame(self, *, lookback_days: int) -> pd.DataFrame:
        # Re-load each call so dashboard views include latest router writes.
        self.tca_db = TCADatabase(self.tca_db_path)
        return self._normalize_frame(self.tca_db.as_dataframe(), lookback_days=lookback_days)

    def summary(self, *, lookback_days: int = 30) -> Dict[str, Any]:
        frame = self._frame(lookback_days=lookback_days)
        if frame.empty:
            return _empty_summary()
        return {
            "trades": int(len(frame)),
            "notional_usd": float(frame["notional"].sum()),
            "avg_expected_alpha_bps": float(frame["expected_alpha_bps"].mean()),
            "avg_realized_cost_bps": float(frame["realized_total_bps"].mean()),
            "avg_realized_net_alpha_bps": float(frame["realized_net_alpha_bps"].mean()),
            "estimated_predicted_pnl_usd": float(frame["predicted_pnl_usd"].sum()),
            "estimated_realized_pnl_usd": float(frame["realized_pnl_usd"].sum()),
            "slippage_mape_pct": float(frame["slippage_ape_pct"].mean()),
        }

    @staticmethod
    def _group_rows(frame: pd.DataFrame, *, by: List[str], limit: int) -> List[Dict[str, Any]]:
        if frame.empty:
            return []
        grouped = (
            frame.groupby(by, dropna=False)
            .agg(
                trades=("trade_id", "count"),
                notional_usd=("notional", "sum"),
                expected_alpha_bps=("expected_alpha_bps", "mean"),
                realized_cost_bps=("realized_total_bps", "mean"),
                realized_net_alpha_bps=("realized_net_alpha_bps", "mean"),
                realized_pnl_usd=("realized_pnl_usd", "sum"),
                slippage_mape_pct=("slippage_ape_pct", "mean"),
            )
            .reset_index()
            .sort_values("realized_pnl_usd", ascending=False)
        )
        rows = grouped.head(max(int(limit), 1)).to_dict(orient="records")
        normalized: List[Dict[str, Any]] = []
        for row in rows:
            normalized.append(
                {
                    **{
                        k: (str(v) if k in by else float(v) if isinstance(v, (int, float)) else v)
                        for k, v in row.items()
                    },
                    "trades": int(row["trades"]),
                }
            )
        return normalized

    def leak_alerts(
        self, *, lookback_days: int = 30, min_notional_usd: float = 5000.0
    ) -> List[Dict[str, Any]]:
        frame = self._frame(lookback_days=lookback_days)
        if frame.empty:
            return []
        grouped = (
            frame.groupby(["strategy_id", "exchange"], dropna=False)
            .agg(
                trades=("trade_id", "count"),
                notional_usd=("notional", "sum"),
                realized_net_alpha_bps=("realized_net_alpha_bps", "mean"),
                realized_pnl_usd=("realized_pnl_usd", "sum"),
            )
            .reset_index()
        )
        flagged = grouped[
            (grouped["notional_usd"] >= float(min_notional_usd))
            & (grouped["realized_net_alpha_bps"] < 0.0)
        ].sort_values("realized_pnl_usd", ascending=True)
        return [
            {
                "strategy_id": str(row["strategy_id"]),
                "exchange": str(row["exchange"]),
                "trades": int(row["trades"]),
                "notional_usd": float(row["notional_usd"]),
                "realized_net_alpha_bps": float(row["realized_net_alpha_bps"]),
                "realized_pnl_usd": float(row["realized_pnl_usd"]),
                "severity": (
                    "high"
                    if float(row["realized_net_alpha_bps"]) < -5.0
                    else "medium" if float(row["realized_net_alpha_bps"]) < -2.0 else "low"
                ),
            }
            for _, row in flagged.iterrows()
        ]

    def payload(self, *, lookback_days: int = 30, limit: int = 25) -> Dict[str, Any]:
        frame = self._frame(lookback_days=lookback_days)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lookback_days": int(lookback_days),
            "summary": self.summary(lookback_days=lookback_days),
            "by_strategy": self._group_rows(frame, by=["strategy_id"], limit=limit),
            "by_venue": self._group_rows(frame, by=["exchange"], limit=limit),
            "by_symbol": self._group_rows(frame, by=["symbol"], limit=limit),
            "by_strategy_venue": self._group_rows(
                frame,
                by=["strategy_id", "exchange"],
                limit=limit,
            ),
            "leak_alerts": self.leak_alerts(lookback_days=lookback_days),
        }
