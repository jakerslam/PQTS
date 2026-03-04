# PQTS - Protheus Quant Trading System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Paper%20Trading-yellow.svg)]()

> A professional-grade algorithmic trading platform for crypto, equities, and forex markets.

## 🚀 Features

- **Multi-Market Support**: Trade crypto, stocks, and forex from one platform
- **10 Strategy Channels**: Scalping, arbitrage, trend following, mean reversion, ML, volume profile, regime detection, order flow, liquidity sweeps, multi-timeframe
- **Universal Indicators**: Technical analysis that works across all markets
- **Risk Management**: Institutional-grade position sizing (Kelly criterion) and drawdown controls
- **Machine Learning**: Ensemble models with online learning
- **Backtesting Framework**: Event-driven backtesting with realistic execution
- **Real-time Dashboard**: Live P&L and performance metrics
- **Paper Trading**: Test risk-free before going live

## 📊 Quick Start

```bash
# Clone and setup
git clone https://github.com/jakerslam/pqts.git
cd pqts

# Recommended: bootstrap local venv + dependencies
make setup
source .venv/bin/activate
# Optional strict lock install:
# make setup-lock

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Start dashboard
python dashboard/start.py

# Run paper trading
python main.py config/paper.yaml
```

## ⚡ One-Command Demo

```bash
make demo
# or:
python demo.py --market crypto --strat ml-ensemble --source x_launch_thread
```

The demo runs a deterministic paper-simulation slice, emits:

- a markdown demo report in `data/reports/`
- a Protheus handoff blob for agent-pilot workflows
- an attribution event row in `data/analytics/attribution_events.jsonl`

## 🧪 Simulation Suite + Telemetry

Run multi-market, multi-strategy simulation suites and emit optimization telemetry:

```bash
make sim-suite
# or:
python scripts/run_simulation_suite.py \
  --markets crypto,equities,forex \
  --strategies market_making,funding_arbitrage,cross_exchange \
  --cycles-per-scenario 60 \
  --readiness-every 20
```

Artifacts:

- suite report JSON: `data/reports/simulation_suite_<timestamp>.json`
- optimization leaderboard CSV: `data/reports/simulation_leaderboard_<timestamp>.csv`
- event telemetry log: `data/analytics/simulation_events.jsonl`

The dashboard now renders this telemetry in a dedicated **Simulation Leaderboard** panel.

Execution drift report:

```bash
python scripts/execution_drift_report.py --tca-db data/tca_records.csv --lookback-days 30
```

Shadow parity + operational SLO flow:

```bash
# 1) Collect market/order/fill parity telemetry
python scripts/run_shadow_stream_worker.py --cycles 30 --sleep-seconds 1.0

# 2) Reconcile internal vs venue state (auto-halt on mismatch)
python scripts/run_reconciliation_daemon.py --cycles 12 --sleep-seconds 5.0 --halt-on-mismatch

# 3) Evaluate SLO health + route alerts
python scripts/slo_health_report.py

# 4) Weekly error-budget review
python scripts/weekly_error_budget_review.py --window-days 7
```

Additional artifacts:

- `data/analytics/shadow_stream_events.jsonl`
- `data/analytics/stream_health.json`
- `data/analytics/reconciliation_incidents.jsonl`
- `data/alerts/slo_alerts.jsonl`
- `data/reports/slo_health_<timestamp>.json`
- `data/reports/error_budget_review_<timestamp>.json`

Execution truth + promotion + canary ramp flow:

```bash
# 1) websocket market/order/fill ingestion
python scripts/run_ws_ingestion.py --cycles 30 --sleep-seconds 1.0

# 2) strategy tournament from partitioned data lake
python scripts/run_strategy_tournament.py \
  --start 2026-01-01T00:00:00Z \
  --end 2026-02-01T00:00:00Z \
  --sources binance:BTCUSDT,binance:ETHUSDT \
  --strategy-types market_making,funding_arbitrage

# 3) policy-driven canary allocation step (advance/hold/rollback/halt)
python scripts/run_canary_ramp.py

# 4) B2B control-plane usage + pricing readout
python scripts/control_plane_report.py
```

## 🎛️ Dashboard

Launch the real-time dashboard:
```bash
python -m streamlit run dashboard/app.py
```

Access at `http://localhost:8501`

## 📈 Strategy Performance

| Strategy | Timeframe | Edge |
|----------|-----------|------|
| Scalping | 1m, 5m | Microstructure, order flow |
| Arbitrage | Real-time | Cross-exchange, funding rates |
| Trend Following | 1h, 4h | Momentum + multi-timeframe |
| Mean Reversion | 15m, 1h | RSI, Bollinger, Volume Profile |
| ML Ensemble | Variable | Random Forest, XGBoost, LSTM |
| Volume Profile | 1h, 4h | POC, Value Area, HVN |
| Order Flow | Tick | Delta, whale detection |
| Liquidity Sweep | 15m, 1h | Stop hunts, false breakouts |

## 🧠 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PQTS v1.1.0                           │
├─────────────────────────────────────────────────────────┤
│  Markets: Binance, Coinbase, Alpaca (paper/live)          │
│  Strategies: 10 channels, 20+ sub-strategies            │
│  Indicators: 15+ universal technical indicators         │
│  Risk: Kelly sizing, VaR, correlation limits            │
│  ML: Ensemble with online learning                      │
│  Execution: Smart routing, TWAP, maker/taker            │
├─────────────────────────────────────────────────────────┤
│  Backtesting: Event-driven, realistic costs             │
│  Dashboard: Real-time Streamlit interface               │
│  Analytics: Sharpe, drawdown, win rate tracking         │
└─────────────────────────────────────────────────────────┘
```

## 📚 Documentation

- [System Overview](docs/OVERVIEW.md)
- [Backtesting Guide](docs/BACKTESTING.md)
- [Simulation Telemetry](docs/SIMULATION_TELEMETRY.md)
- [World-Class 30/60/90 Plan](docs/WORLD_CLASS_30_60_90.md)
- [Max Utility + Revenue Playbook](docs/MAX_UTILITY_REVENUE_PLAYBOOK.md)
- [Strategy Patterns](docs/ADVANCED_PATTERNS.md)
- [Incident Runbook](docs/INCIDENT_RUNBOOK.md)
- [Pricing And Packaging](docs/PRICING_AND_PACKAGING.md)
- [GTM 90-Day Plan](docs/GTM_90_DAY_PLAN.md)
- [Self-Serve Signup Spec](docs/SELF_SERVE_SIGNUP_SPEC.md)
- [Protheus Toybox Launch](docs/PROTHEUS_TOYBOX.md)
- [X Thread Template](docs/X_THREAD_TEMPLATE.md)

## 🛠️ Configuration

### Paper Trading
```yaml
mode: paper_trading
markets:
  crypto:
    enabled: true
    exchanges:
      - name: binance
        api_key: ${BINANCE_TESTNET_API_KEY}
        api_secret: ${BINANCE_TESTNET_API_SECRET}
        testnet: true
```

### Live Trading
```yaml
mode: live
markets:
  crypto:
    enabled: true
    exchanges:
      - name: binance
        testnet: false
        api_key: ${BINANCE_API_KEY}
        api_secret: ${BINANCE_API_SECRET}
```

## ⚠️ Risk Disclaimer

Trading involves substantial risk. Past performance doesn't guarantee future results. Always start with paper trading.
Any Sharpe/return claim should come from reproducible backtest or paper/live reports.

## 📄 License

Proprietary - Protheus Labs

---

Built with 🔥 by Protheus
