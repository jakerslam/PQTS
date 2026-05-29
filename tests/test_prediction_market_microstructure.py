from __future__ import annotations

from datetime import datetime, timezone

from research.prediction_market_microstructure import (
    PredictionMarketBookSnapshot,
    build_prediction_market_microstructure_features,
)


def _ts(second: int) -> datetime:
    return datetime(2026, 1, 1, 12, 0, second, tzinfo=timezone.utc)


def test_prediction_market_features_compute_spread_parity_and_depth() -> None:
    frame = build_prediction_market_microstructure_features(
        [
            PredictionMarketBookSnapshot(
                market_id="mkt_1",
                outcome_id="yes",
                timestamp=_ts(0),
                yes_bid=0.44,
                yes_ask=0.46,
                yes_bid_size=120.0,
                yes_ask_size=80.0,
                no_bid=0.53,
                no_ask=0.55,
                traded_volume=1000.0,
                liquidity=5000.0,
                source="polymarket_ws",
                sequence=1,
            )
        ]
    )

    row = frame.iloc[0]
    assert row["yes_mid_probability"] == 0.45
    assert round(row["yes_spread_bps"], 2) == 444.44
    assert round(row["yes_no_parity_gap"], 2) == -0.01
    assert round(row["depth_imbalance"], 2) == 0.20
    assert row["quality_flags"] == ()


def test_prediction_market_features_are_point_in_time_and_do_not_emit_resolution_label() -> None:
    frame = build_prediction_market_microstructure_features(
        [
            PredictionMarketBookSnapshot(
                market_id="mkt_1",
                outcome_id="yes",
                timestamp=_ts(0),
                yes_bid=0.40,
                yes_ask=0.42,
                yes_bid_size=10.0,
                yes_ask_size=10.0,
                traded_volume=100.0,
                liquidity=1000.0,
                sequence=1,
                resolved_probability=1.0,
            ),
            PredictionMarketBookSnapshot(
                market_id="mkt_1",
                outcome_id="yes",
                timestamp=_ts(10),
                yes_bid=0.43,
                yes_ask=0.45,
                yes_bid_size=12.0,
                yes_ask_size=8.0,
                traded_volume=130.0,
                liquidity=1100.0,
                sequence=2,
                resolved_probability=1.0,
            ),
        ]
    )

    assert "resolved_probability" not in frame.columns
    assert frame.iloc[0]["prior_yes_mid_probability"] != frame.iloc[0]["prior_yes_mid_probability"]
    assert frame.iloc[1]["prior_yes_mid_probability"] == 0.41000000000000003
    assert round(frame.iloc[1]["yes_mid_delta"], 2) == 0.03
    assert frame.iloc[1]["volume_velocity_per_second"] == 3.0


def test_prediction_market_features_flag_invalid_stale_and_non_monotonic_rows() -> None:
    frame = build_prediction_market_microstructure_features(
        [
            {
                "market_id": "mkt_2",
                "outcome_id": "yes",
                "timestamp": _ts(0),
                "yes_bid": 0.60,
                "yes_ask": 0.50,
                "yes_bid_size": 1.0,
                "yes_ask_size": 2.0,
                "traded_volume": 50.0,
                "liquidity": 0.0,
                "sequence": 1,
            },
            {
                "market_id": "mkt_2",
                "outcome_id": "yes",
                "timestamp": _ts(30),
                "yes_bid": 0.51,
                "yes_ask": 0.52,
                "yes_bid_size": 1.0,
                "yes_ask_size": 2.0,
                "traded_volume": 40.0,
                "liquidity": 0.0,
                "sequence": 2,
            },
        ],
        max_staleness_seconds=5.0,
    )

    assert "invalid_yes_quote" in frame.iloc[0]["quality_flags"]
    assert "stale_snapshot" in frame.iloc[1]["quality_flags"]
    assert "non_monotonic_volume" in frame.iloc[1]["quality_flags"]
