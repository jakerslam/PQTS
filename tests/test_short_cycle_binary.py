from strategies.short_cycle_binary import (
    SecurityHealth,
    ShortCycleBinaryEngine,
    ShortCycleConfig,
    ShortCycleQuote,
    classify_external_claim,
)


def _quote(*, market_id: str = "m1", ts: int = 1_000, depth: float = 150.0) -> ShortCycleQuote:
    return ShortCycleQuote(
        market_id=market_id,
        asset="BTC",
        interval="5m",
        ask_yes=0.47,
        ask_no=0.50,
        yes_depth=depth,
        no_depth=depth,
        timestamp_ms=ts,
        fee_buffer=0.005,
        slippage_buffer=0.005,
    )


def test_bundle_scanner_detects_edge_and_filters_stale() -> None:
    engine = ShortCycleBinaryEngine(ShortCycleConfig(min_bundle_edge=0.01, stale_limit_ms=500))
    signals = engine.scan_bundle([_quote(ts=1_000)], now_ms=1_200)
    assert len(signals) == 1
    assert signals[0].bundle_edge > 0.01

    stale = engine.scan_bundle([_quote(ts=100)], now_ms=1_200)
    assert stale == []


def test_legging_and_single_leg_controls() -> None:
    ok, reason = ShortCycleBinaryEngine.validate_legging(
        execution_window_ms=250,
        max_legging_ms=500,
        unhedged_notional=20.0,
        max_unhedged_notional=50.0,
    )
    assert ok and reason == "ok"

    bad, reason = ShortCycleBinaryEngine.validate_legging(
        execution_window_ms=600,
        max_legging_ms=500,
        unhedged_notional=20.0,
        max_unhedged_notional=50.0,
    )
    assert not bad and reason == "legging_time_exceeded"

    disabled_engine = ShortCycleBinaryEngine()
    allowed, reason = disabled_engine.evaluate_single_leg_mode(edge=0.03, all_existing_gates_pass=True)
    assert not allowed and reason == "single_leg_disabled"

    enabled_engine = ShortCycleBinaryEngine(ShortCycleConfig(single_leg_enabled=True, min_single_leg_edge=0.02))
    allowed, reason = enabled_engine.evaluate_single_leg_mode(edge=0.03, all_existing_gates_pass=True)
    assert allowed and reason == "ok"


def test_micro_edge_metrics_and_disable() -> None:
    engine = ShortCycleBinaryEngine(ShortCycleConfig(edge_floor_for_disable=0.001))
    engine.record_outcome(executed=True, realized_edge=0.002)
    engine.record_outcome(executed=False, rejected=True)
    metrics = engine.metrics()
    assert metrics["opportunities_detected"] == 2.0
    assert metrics["opportunities_executed"] == 1.0
    assert metrics["reject_rate"] > 0.0
    assert not engine.should_disable()

    engine_low = ShortCycleBinaryEngine(ShortCycleConfig(edge_floor_for_disable=0.003))
    engine_low.record_outcome(executed=True, realized_edge=0.001)
    assert engine_low.should_disable()


def test_security_health_and_claim_classification() -> None:
    engine = ShortCycleBinaryEngine()
    ok, reason = engine.security_health_passed(
        SecurityHealth(
            private_control_plane=True,
            operator_allowlist_enabled=True,
            command_allowlist_enabled=True,
            sandbox_isolation_enabled=True,
            least_privilege_scopes=True,
        )
    )
    assert ok and reason == "ok"

    bad, reason = engine.security_health_passed(
        SecurityHealth(
            private_control_plane=False,
            operator_allowlist_enabled=True,
            command_allowlist_enabled=True,
            sandbox_isolation_enabled=True,
            least_privilege_scopes=True,
        )
    )
    assert not bad and reason == "public_admin_ingress_disallowed"
    assert classify_external_claim(True, True) == "observed"
    assert classify_external_claim(False, True) == "inferred"
    assert classify_external_claim(False, False) == "unverified"


def test_frequency_kelly_expansion_and_exogenous_controls() -> None:
    engine = ShortCycleBinaryEngine(ShortCycleConfig(max_orders_per_minute=2, max_trades_per_day=2))
    engine.record_order_activity(timestamp_ms=1_000, trade_executed=True)
    engine.record_order_activity(timestamp_ms=1_100, trade_executed=True)
    engine.record_order_activity(timestamp_ms=1_200, trade_executed=False)
    ok, reason = engine.frequency_governance(now_ms=1_200)
    assert not ok and reason == "orders_per_minute_exceeded"

    sizing = engine.kelly_constrained_fraction(
        win_probability=0.58,
        payout_multiple=1.2,
        kelly_fraction_cap=0.25,
        hard_risk_cap=0.10,
    )
    assert sizing["approved_fraction"] <= 0.10

    engine.allowed_expansion_assets.add("ETH")
    expand_ok, reason = engine.can_expand_asset(
        asset="ETH",
        readiness_checks={
            "liquidity_depth": True,
            "slippage_stability": True,
            "risk_capacity_fit": True,
            "regression_checks": True,
        },
    )
    assert expand_ok and reason == "ok"

    feed_ok, reason = engine.validate_exogenous_feed(
        source_quality="observed",
        sample_timestamp_ms=1_000,
        now_ms=1_500,
        max_age_ms=1_000,
    )
    assert feed_ok and reason == "ok"
