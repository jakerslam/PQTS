# Protheus Quant Trading System (PQTS)

## Overview
A professional-grade algorithmic trading platform for crypto, equities, and forex markets.
Built with institutional-quality risk management, machine learning prediction, and comprehensive analytics.

## Architecture

```
pqts/
├── core/                    # Core trading engine
│   ├── engine.py           # Main execution engine
│   ├── portfolio.py        # Portfolio management
│   ├── risk_manager.py     # Risk controls
│   └── config.py           # Configuration management
├── markets/                 # Market adapters
│   ├── crypto/             # Crypto exchanges (Binance, Coinbase, etc.)
│   ├── equities/           # Stock markets (Alpaca, IBKR, etc.)
│   └── forex/              # FX markets (OANDA, etc.)
├── strategies/              # Trading strategies
│   ├── base.py             # Base strategy class
│   ├── scalping/           # Scalping strategies
│   ├── arbitrage/          # Arbitrage strategies
│   ├── trend_following/    # Trend strategies
│   ├── mean_reversion/     # Mean reversion
│   └── ml/                 # ML-based strategies
├── indicators/              # Technical indicators
│   ├── universal.py        # Universal indicators (works across all markets)
│   └── specialized/        # Market-specific adaptations
├── data/                    # Data management
│   ├── ingestion.py        # Real-time data feeds
│   ├── storage.py          # Time-series database
│   └── features.py         # Feature engineering
├── ml/                      # Machine learning
│   ├── models/             # Prediction models
│   ├── training.py         # Model training pipeline
│   └── evaluation.py       # Backtesting & evaluation
├── analytics/               # Analytics & dashboard
│   ├── dashboard.py        # Real-time dashboard
│   ├── reports.py          # Performance reports
│   └── visualization.py    # Charts & plots
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── backtest/           # Backtest validation
└── docs/                    # Documentation
    ├── api/                # API documentation
    ├── strategies/         # Strategy guides
    └── deployment/         # Deployment guides
```

## Key Features

### Multi-Market Support
- **Crypto**: Spot, futures, perpetuals (Binance, Coinbase Pro, Kraken)
- **Equities**: US stocks, ETFs (Alpaca, Interactive Brokers)
- **Forex**: Major pairs, crosses (OANDA, Forex.com)

### Strategy Channels

#### Scalping
- Order book imbalance
- Microstructure noise exploitation
- Latency arbitrage

#### Arbitrage
- Cross-exchange arbitrage
- Triangular arbitrage
- Statistical arbitrage (pairs trading)
- Funding rate arbitrage

#### Trend Following
- Multi-timeframe momentum
- Breakout detection
- Moving average crossovers

#### Mean Reversion
- Bollinger Bands
- RSI oversold/overbought
- Statistical arbitrage

### Universal Indicators
All indicators normalized to work across crypto, equities, and forex:
- Price action (OHLCV normalized)
- Volatility measures (ATR, realized vol)
- Momentum (RSI, MACD, stochastic)
- Volume profiles
- Order flow (where available)

### Machine Learning
- Online learning (models update continuously)
- Ensemble methods (Random Forest, XGBoost, LSTM)
- Feature importance tracking
- Model drift detection

### Risk Management
- Position sizing (Kelly criterion, risk parity)
- Stop losses (trailing, volatility-based)
- Drawdown controls
- Correlation monitoring
- Maximum exposure limits

### Analytics Dashboard
- Real-time P&L
- Position tracking
- Strategy performance
- Risk metrics (VaR, Sharpe, Sortino)
- Market regime detection

## Configuration

```yaml
# config/production.yaml
mode: paper_trading  # paper_trading | live

markets:
  crypto:
    enabled: true
    exchanges:
      - name: binance
        api_key: ${BINANCE_API_KEY}
        api_secret: ${BINANCE_API_SECRET}
        testnet: true
  equities:
    enabled: true
    brokers:
      - name: alpaca
        api_key: ${ALPACA_API_KEY}
        api_secret: ${ALPACA_API_SECRET}
        paper: true
  forex:
    enabled: true
    brokers:
      - name: oanda
        api_key: ${OANDA_API_KEY}
        account_id: ${OANDA_ACCOUNT_ID}

strategies:
  scalping:
    enabled: true
    max_positions: 5
    timeframes: [1m, 5m]
  arbitrage:
    enabled: true
    min_spread_pct: 0.1
  trend_following:
    enabled: true
    timeframes: [1h, 4h, 1d]
  mean_reversion:
    enabled: true
    lookback: 20

risk:
  max_portfolio_risk_pct: 2.0
  max_position_risk_pct: 1.0
  max_drawdown_pct: 10.0
  max_correlation: 0.7

ml:
  enabled: true
  model_type: ensemble
  retrain_interval_hours: 24
  prediction_horizon: 1h
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run paper trading
python -m pqts.core.engine --mode paper --config config/paper.yaml

# Start dashboard
python -m pqts.analytics.dashboard
```

## Development

```bash
# Run tests
pytest tests/

# Backtest strategy
python -m pqts.ml.backtest --strategy trend_following --start 2024-01-01 --end 2024-12-31

# Train ML model
python -m pqts.ml.training --model ensemble --data data/historical
```

## License
Proprietary - Protheus Labs
