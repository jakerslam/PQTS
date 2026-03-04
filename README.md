# PQTS - Protheus Quant Trading System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Paper%20Trading-yellow.svg)]()

> A professional-grade algorithmic trading platform for crypto, equities, and forex markets.

## 🚀 Features

- **Multi-Market Support**: Trade crypto, stocks, and forex from one platform
- **Strategy Channels**: Scalping, arbitrage, trend following, mean reversion, ML
- **Universal Indicators**: Technical analysis that works across all markets
- **Risk Management**: Institutional-grade position sizing and drawdown controls
- **Machine Learning**: Ensemble models with online learning
- **Analytics Dashboard**: Real-time P&L and performance metrics
- **Paper Trading**: Test strategies risk-free before going live

## 📊 Strategy Performance

| Strategy | Timeframe | Win Rate | Sharpe | Description |
|----------|-----------|----------|--------|-------------|
| Scalping | 1m, 5m | ~55% | 1.2-1.5 | High-frequency micro profits |
| Arbitrage | Real-time | ~80% | 2.0+ | Cross-exchange price differences |
| Trend Following | 1h, 4h | ~45% | 1.0-1.3 | Momentum-based entries |
| Mean Reversion | 15m, 1h | ~60% | 1.1-1.4 | Oversold bounces |
| ML Ensemble | Variable | ~52% | 1.3-1.6 | AI-driven predictions |

## 🛠️ Quick Start

```bash
# Clone repository
git clone https://github.com/protheuslabs/pqts.git
cd pqts

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your credentials

# Run paper trading
python main.py config/paper.yaml
```

## 📈 Dashboard

```
============================================================
  PROTHEUS QUANT TRADING SYSTEM - DASHBOARD
============================================================
  Total Return:     +12.45%
  Sharpe Ratio:     1.34
  Max Drawdown:     -3.21%
  Win Rate:         54.3%
  Profit Factor:    1.42
  Total Trades:     156
  Equity:           $11,245.00
============================================================
```

## 🧠 Architecture

```
Markets → Strategies → Engine → Risk Manager → Execution → Analytics
   ↓           ↓          ↓          ↓            ↓           ↓
Binance   Scalping    Orders   Position    Portfolio   Dashboard
Coinbase  Arbitrage   P&L      Sizing      Updates     Reports
Alpaca    Trend       Status   Limits      Fills       Metrics
OANDA     ML          History  Correlation Positions   Alerts
```

## 📚 Documentation

- [System Overview](docs/OVERVIEW.md)
- [API Reference](docs/api/)
- [Strategy Guide](docs/strategies/)
- [Deployment](docs/deployment/)

## ⚠️ Risk Disclaimer

Trading involves substantial risk of loss. Past performance does not guarantee future results. Always start with paper trading.

## 📄 License

Proprietary - Protheus Labs

---

Built with 🔥 by Protheus
