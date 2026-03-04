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
git clone https://github.com/protheuslabs/pqts.git
cd pqts
pip install -r requirements.txt
# Or strict install with hashes:
pip install --require-hashes -r requirements.lock

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Start dashboard
python dashboard/start.py

# Run paper trading
python main.py config/paper.yaml
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
- [Strategy Patterns](docs/ADVANCED_PATTERNS.md)
- [Incident Runbook](docs/INCIDENT_RUNBOOK.md)
- [Pricing And Packaging](docs/PRICING_AND_PACKAGING.md)
- [GTM 90-Day Plan](docs/GTM_90_DAY_PLAN.md)
- [Self-Serve Signup Spec](docs/SELF_SERVE_SIGNUP_SPEC.md)

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

## 📄 License

Proprietary - Protheus Labs

---

Built with 🔥 by Protheus
