use pyo3::prelude::*;
use sha2::{Digest, Sha256};

fn clamp_lower(value: f64, floor: f64) -> f64 {
    if value.is_finite() {
        value.max(floor)
    } else {
        floor
    }
}

fn sha256_hex(seed: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(seed.as_bytes());
    let digest = hasher.finalize();
    let mut out = String::with_capacity(64);
    for byte in digest {
        out.push_str(&format!("{:02x}", byte));
    }
    out
}

#[pyfunction]
fn version() -> String {
    "pqts_hotpath 0.1.0".to_string()
}

#[pyfunction]
fn sum_notional(levels: Vec<(f64, f64)>, max_levels: usize) -> f64 {
    let mut total: f64 = 0.0;
    let limit = if max_levels == 0 { 1 } else { max_levels };
    for (idx, (price, size)) in levels.iter().enumerate() {
        if idx >= limit {
            break;
        }
        let p = if *price > 0.0 { *price } else { 0.0 };
        let q = if *size > 0.0 { *size } else { 0.0 };
        total += p * q;
    }
    total
}

#[pyfunction]
fn fill_metrics(
    side: &str,
    reference_price: f64,
    executed_price: f64,
    requested_qty: f64,
    executed_qty: f64,
) -> (f64, f64) {
    let ref_denom = if reference_price > 1e-12 {
        reference_price
    } else {
        1e-12
    };
    let side_token = side.to_ascii_lowercase();
    let slip_pct = if side_token == "buy" {
        ((executed_price - reference_price) / ref_denom).max(0.0)
    } else {
        ((reference_price - executed_price) / ref_denom).max(0.0)
    };
    let req_denom = if requested_qty > 1e-12 {
        requested_qty
    } else {
        1e-12
    };
    (slip_pct * 10000.0, executed_qty / req_denom)
}

#[pyfunction(signature = (received_sequence, allow_auto_recover, expected_sequence=None, snapshot_sequence=None))]
fn sequence_transition(
    received_sequence: i64,
    allow_auto_recover: bool,
    expected_sequence: Option<i64>,
    snapshot_sequence: Option<i64>,
) -> (String, i64, i64, bool, Option<i64>, i64) {
    match expected_sequence {
        None => {
            let next_expected = received_sequence + 1;
            (
                "seed".to_string(),
                next_expected,
                0,
                false,
                None,
                next_expected,
            )
        }
        Some(expected) => {
            if received_sequence < expected {
                ("stale_drop".to_string(), expected, 0, false, None, expected)
            } else if received_sequence == expected {
                (
                    "in_order".to_string(),
                    expected,
                    0,
                    false,
                    None,
                    received_sequence + 1,
                )
            } else {
                let gap_size = received_sequence - expected;
                if allow_auto_recover {
                    if let Some(snapshot) = snapshot_sequence {
                        let next_expected = snapshot + 1;
                        return (
                            "gap_recovered_snapshot".to_string(),
                            expected,
                            gap_size,
                            true,
                            Some(snapshot),
                            next_expected,
                        );
                    }
                }
                (
                    "gap_detected".to_string(),
                    expected,
                    gap_size,
                    false,
                    None,
                    expected,
                )
            }
        }
    }
}

#[pyfunction]
fn uniform_from_seed(seed: &str) -> f64 {
    let hex = sha256_hex(seed);
    let prefix = &hex[..8];
    let value = u32::from_str_radix(prefix, 16).unwrap_or(0);
    (value as f64) / 4294967295.0
}

#[pyfunction]
fn event_id_hash(prefix: &str, payload: &str, hex_len: usize) -> String {
    let mut token = sha256_hex(payload);
    let take = hex_len.clamp(1, 64);
    token.truncate(take);
    format!("{}_{}", prefix, token)
}

#[pyfunction]
fn paper_fill_metrics(
    side: &str,
    requested_qty: f64,
    reference_price: f64,
    queue_qty: f64,
    partial_fill_notional_usd: f64,
    min_partial_fill_ratio: f64,
    queue_penalty_floor: f64,
    adverse_selection_bps: f64,
    min_slippage_bps: f64,
    queue_slippage_bps_per_turnover: f64,
    reality_stress_mode: bool,
    stress_fill_ratio_multiplier: f64,
    stress_slippage_multiplier: f64,
    fill_uniform: f64,
    slippage_uniform: f64,
) -> (f64, f64, f64, f64, f64) {
    let req_qty = clamp_lower(requested_qty, 0.0);
    let ref_price = clamp_lower(reference_price, 0.0);
    let queue = clamp_lower(queue_qty, 0.0);
    let partial = clamp_lower(partial_fill_notional_usd, 1e-9);
    let min_fill = clamp_lower(min_partial_fill_ratio, 0.0).min(1.0);

    let notional = req_qty * ref_price;
    let base_fill_ratio = if notional <= partial {
        1.0
    } else {
        let capacity_ratio = (partial / clamp_lower(notional, 1e-9)).clamp(min_fill, 1.0);
        let jitter = 0.9 + (0.2 * fill_uniform);
        (capacity_ratio * jitter).clamp(min_fill, 1.0)
    };

    let queue_notional = queue * ref_price;
    let order_notional = (req_qty * ref_price).max(1e-9);
    let queue_turnover = if queue_notional <= 0.0 {
        0.0
    } else {
        order_notional / queue_notional
    };
    let queue_penalty = clamp_lower(queue_penalty_floor, 0.0).max(1.0 / (1.0 + queue_turnover.max(0.0)));

    let mut fill_ratio = base_fill_ratio * queue_penalty;
    if reality_stress_mode {
        fill_ratio = (fill_ratio * clamp_lower(stress_fill_ratio_multiplier, 0.0)).clamp(0.0, 1.0);
    }

    let impact_scale = ((notional / partial) - 1.0).max(0.0);
    let stochastic_component = (slippage_uniform - 0.5) * 0.6;
    let mut slip_bps = clamp_lower(adverse_selection_bps, 0.0) * (0.5 + impact_scale) + stochastic_component;
    slip_bps += clamp_lower(queue_slippage_bps_per_turnover, 0.0) * queue_turnover.max(0.0);
    slip_bps = slip_bps.max(clamp_lower(min_slippage_bps, 0.0));
    if reality_stress_mode {
        slip_bps *= clamp_lower(stress_slippage_multiplier, 0.0);
    }

    let executed_qty = req_qty * fill_ratio;
    let side_token = side.to_ascii_lowercase();
    let executed_price = if side_token == "buy" {
        ref_price * (1.0 + (slip_bps / 10000.0))
    } else {
        ref_price * (1.0 - (slip_bps / 10000.0))
    };
    (
        fill_ratio,
        slip_bps,
        executed_qty,
        executed_price,
        queue_turnover.max(0.0),
    )
}

fn depth_and_best(levels: &[(f64, f64)], max_levels: usize) -> (f64, f64, f64) {
    let mut total = 0.0;
    let mut best_price = 0.0;
    let mut best_size = 0.0;
    let mut count = 0usize;
    for (price, size) in levels.iter() {
        if count >= max_levels {
            break;
        }
        let p = if price.is_finite() && *price > 0.0 { *price } else { 0.0 };
        let q = if size.is_finite() && *size > 0.0 { *size } else { 0.0 };
        if count == 0 {
            best_price = p;
            best_size = q;
        }
        total += p * q;
        count += 1;
    }
    (total, best_price, best_size)
}

#[pyfunction]
fn book_metrics(
    bids: Vec<(f64, f64)>,
    asks: Vec<(f64, f64)>,
    max_levels: usize,
) -> (f64, f64, f64, f64, f64, f64) {
    let depth_limit = if max_levels == 0 { 1 } else { max_levels };
    let (bid_depth, best_bid, bid_size) = depth_and_best(&bids, depth_limit);
    let (ask_depth, best_ask, ask_size) = depth_and_best(&asks, depth_limit);
    let mut mid = 0.0;
    if best_bid > 0.0 && best_ask > 0.0 {
        mid = (best_bid + best_ask) / 2.0;
    }
    let mid_price = if mid > 0.0 { mid } else { 1e-9 };
    let spread_bps = if best_bid > 0.0 && best_ask > 0.0 {
        ((best_ask - best_bid) / mid_price) * 10000.0
    } else {
        0.0
    };
    (
        mid_price,
        spread_bps,
        bid_depth,
        ask_depth,
        bid_size,
        ask_size,
    )
}

#[pyfunction]
fn smart_router_score(
    spread: f64,
    volume_24h: f64,
    fee_bps: f64,
    slippage_ratio: f64,
    fill_ratio: f64,
    latency_ms: f64,
) -> f64 {
    let spread_score = 1.0 / (1.0 + clamp_lower(spread, 0.0) * 100.0);
    let volume_score = (clamp_lower(volume_24h, 0.0) / 1_000_000.0).min(1.0);
    let fee_score = 1.0 / (1.0 + fee_bps.max(-5.0) / 10.0);

    let slippage = clamp_lower(slippage_ratio, 0.25);
    let fill = clamp_lower(fill_ratio, 0.0).min(1.0);
    let latency = clamp_lower(latency_ms, 0.0);
    let quality_score =
        (1.0 / slippage) * 0.5 + fill * 0.3 + (1.0 / (1.0 + latency / 500.0)) * 0.2;

    spread_score * 0.30 + volume_score * 0.30 + fee_score * 0.20 + quality_score * 0.20
}

#[pyfunction]
fn quote_state(price: f64, age_seconds: f64, stale_after_seconds: f64) -> (bool, bool) {
    let valid_price = price.is_finite() && price > 0.0;
    let age = if age_seconds.is_finite() {
        age_seconds.max(0.0)
    } else {
        f64::INFINITY
    };
    let stale_after = if stale_after_seconds.is_finite() {
        stale_after_seconds.max(0.0)
    } else {
        0.0
    };
    let stale = age > stale_after;
    (stale, valid_price && !stale)
}

#[pyfunction]
fn profitability_net_alpha_bps(
    expected_alpha_bps: f64,
    expected_cost_usd: f64,
    expected_slippage_usd: f64,
    notional_usd: f64,
    min_edge_bps: f64,
) -> (f64, f64, f64) {
    let notional = clamp_lower(notional_usd, 1e-12);
    let total_router_bps = ((clamp_lower(expected_cost_usd, 0.0) + clamp_lower(expected_slippage_usd, 0.0))
        / notional)
        * 10000.0;
    let net_alpha_bps = expected_alpha_bps - total_router_bps;
    let required_alpha_bps = total_router_bps + clamp_lower(min_edge_bps, 0.0);
    (total_router_bps, net_alpha_bps, required_alpha_bps)
}

#[pymodule]
fn pqts_hotpath(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(sum_notional, m)?)?;
    m.add_function(wrap_pyfunction!(fill_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(book_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(sequence_transition, m)?)?;
    m.add_function(wrap_pyfunction!(uniform_from_seed, m)?)?;
    m.add_function(wrap_pyfunction!(event_id_hash, m)?)?;
    m.add_function(wrap_pyfunction!(paper_fill_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(smart_router_score, m)?)?;
    m.add_function(wrap_pyfunction!(quote_state, m)?)?;
    m.add_function(wrap_pyfunction!(profitability_net_alpha_bps, m)?)?;
    Ok(())
}
