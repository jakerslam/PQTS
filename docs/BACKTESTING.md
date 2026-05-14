# PQTS Backtesting Framework

Event-driven backtesting engine for validating trading strategies.

## Features

- **Realistic Execution**: Simulates slippage, commissions, and market impact
- **Walk-Forward Analysis**: Tests strategies on out-of-sample data
- **Position Tracking**: Maintains realistic position state and P&L
- **Performance Metrics**: Calculates Sharpe, drawdown, win rate, etc.
- **Trade Log**: Records all trades for detailed analysis

## Usage

```python
from backtesting.engine import BacktestingEngine
from datetime import datetime

# Initialize
engine = BacktestingEngine({
    'data_dir': 'data/historical',
    'commission_rate': 0.001,  # 0.1%
    'slippage_bps': 5  # 5 basis points
})

# Define strategy
def my_strategy(market_data, historical_df):
    signals = []
    current = market_data['close']
    sma20 = historical_df['close'].rolling(20).mean().iloc[-1]
    
    if current > sma20:
        signals.append({
            'symbol': 'BTCUSDT',
            'direction': 'long',
            'quantity': 0.1
        })
    
    return signals

# Run backtest
result = engine.run_backtest(
    strategy=my_strategy,
    symbol='BTCUSDT',
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 3, 31),
    initial_capital=10000.0
)

# View results
print(f"Return: {result.total_return_pct:.2f}%")
print(f"Sharpe: {result.sharpe_ratio:.2f}")
print(f"Max DD: {result.max_drawdown_pct:.2f}%")
print(f"Trades: {result.total_trades}")

# Save results
engine.save_results(result, 'backtest_btc_q1.json')
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `data_dir` | data/historical | Historical data directory |
| `commission_rate` | 0.001 | Trading commission (0.1%) |
| `slippage_bps` | 5 | Slippage in basis points |
| `slippage_model` | fixed | Slippage model (fixed/volume) |

## Historical Data Format

CSV format with columns:
```csv
timestamp,open,high,low,close,volume
2024-01-01 00:00:00,43500,43800,43200,43600,1500.5
```

## Download Historical Data

Use the built-in downloader to fetch Binance/Coinbase OHLCV with pagination and manifest checks:

```bash
python3 scripts/download_historical_data.py \
  --venue all \
  --binance-symbols BTCUSDT,ETHUSDT \
  --coinbase-symbols BTC-USD,ETH-USD \
  --interval 1h \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --output-dir data/historical \
  --format csv
```

Output layout:

```text
data/historical/<venue>/<symbol>/<interval>/<YYYYMMDD_YYYYMMDD>.csv
data/historical/<venue>/<symbol>/<interval>/<YYYYMMDD_YYYYMMDD>.manifest.json
```

## Paper Readiness Gate

Generate a paper-live readiness report from realized fills (track record + slippage thresholds):

```bash
python3 scripts/paper_readiness_report.py \
  --tca-db data/tca_records.csv \
  --lookback-days 60 \
  --min-days 30 \
  --min-fills 200 \
  --max-p95-slippage-bps 20 \
  --max-mape-pct 35 \
  --out-dir data/reports
```

`ready_for_canary` is true only if:
- Track record gate passes (`trading_days >= min_days` and `fills >= min_fills`)
- Slippage gate passes (`p95_realized_slippage_bps <= max_p95` and `MAPE <= max_mape`)

## Continuous Paper Campaign

Run continuous probe orders through `RiskAwareRouter.submit_order()` to accumulate real paper fills and readiness snapshots:

```bash
python3 scripts/run_paper_campaign.py \
  --config config/paper.yaml \
  --symbols BTCUSDT,ETHUSDT,BTC-USD,ETH-USD \
  --cycles 5000 \
  --sleep-seconds 60 \
  --notional-usd 200 \
  --paper-stress-multiplier 3.0 \
  --paper-stress-fill-ratio-multiplier 0.70 \
  --readiness-every 100 \
  --out-dir data/reports
```

This writes rolling readiness snapshots:

```text
data/reports/paper_campaign_snapshot_<timestamp>.json
```

## Live Market Data / Paper Execution

For a clean live-data run without real order placement, use the Coinbase public
market-data config:

```bash
python3 main.py config/live_data.yaml
```

This config enables only Coinbase crypto symbols with `public_market_data: true`.
The router consumes live public quotes while `mode: paper_trading` keeps order
execution simulated. Exchange credentials are still required before any
authenticated or live-money order path can run.

`config/live_data.yaml` fails closed when live quotes are unresolved or outside
configured per-symbol price sanity bounds. The router may replay a recent good
quote inside the resilience window, but it will not synthesize tradable BTC/ETH/SOL
prices for this live-data paper path.

Paper validation should use strategy/research-derived expected alpha:

```bash
python3 scripts/run_paper_campaign.py \
  --config config/live_data.yaml \
  --symbols BTC-USD,ETH-USD,SOL-USD \
  --research-report data/research_reports/<run>/report.json \
  --require-research-alpha
```

`--campaign-expected-alpha-bps` remains available only for simulation-only
plumbing probes. Reports label that source as `cli_override` so it cannot be
mistaken for strategy evidence.

Each snapshot now includes:
- `ops_health`: deterministic critical/warning incident checks
- `promotion_gate`: explicit `promote_to_live_canary | remain_in_paper | reject_or_research`
- `reliability`: per-venue degradation telemetry
- `market_data_resilience`: replay/failover/sanity-reject/synthetic/unresolved quote counts

Generate a compact soak report from a snapshot and TCA file:

```bash
python3 scripts/live_data_soak_report.py \
  --reports-dir data/reports/live_data_soak_<run_id> \
  --tca-path data/live_data_soak_<run_id>_tca.csv \
  --out-dir data/reports/live_data_soak_<run_id>
```

Download backdated Coinbase candles for replay/research validation:

```bash
python3 scripts/download_historical_data.py \
  --venue coinbase \
  --coinbase-symbols BTC-USD,ETH-USD,SOL-USD \
  --interval 1h \
  --start 2024-01-01 \
  --end 2026-05-01 \
  --output-dir data/historical
```

Run the full real-data validation ladder before any live-money decision:

```bash
python3 scripts/run_real_money_validation.py \
  --venue coinbase \
  --symbols BTC-USD,ETH-USD,SOL-USD \
  --interval 1h \
  --start 2024-05-10 \
  --end 2026-05-10 \
  --run-paper-smoke
```

The ladder writes immutable evidence under `data/reports/real_money_validation_<run_id>/`.
It first enforces historical data quality, then runs the research tournament,
builds a research-validation payload, and only starts the live-data paper smoke
when OOS/CV/deflated-Sharpe and expected-alpha gates are promotable. The default
strategy universe includes aggregate legacy families plus symbol-aware
`cross_sectional_momentum`, `adaptive_trend`, and `drawdown_reversion` families
that can rotate among assets or sit in cash without bypassing promotion gates.
It also includes the research-only `markov_regime` family, which implements the
observable Markov-chain framework as rolling bull/bear/sideways state labels,
walk-forward transition-matrix estimation, multi-step regime probability
forecasts, and long-only allocation to assets with positive bull-minus-bear
transition edge. It is not a live shortcut: candidates still need purged CV,
deflated Sharpe, walk-forward validation, paper duration, slippage, and
kill-switch gates before any staged promotion.

## Daily Ops Wrapper

Run campaign + readiness as one daily operation:

```bash
python3 scripts/daily_paper_ops.py \
  --config config/paper.yaml \
  --campaign-symbols BTCUSDT,ETHUSDT,BTC-USD,ETH-USD \
  --campaign-cycles 1440 \
  --campaign-sleep-seconds 60 \
  --campaign-notional-usd 150 \
  --campaign-readiness-every 60 \
  --paper-stress-multiplier 3.0 \
  --paper-stress-fill-ratio-multiplier 0.70 \
  --require-no-critical-alerts \
  --out-dir data/reports
```

Example cron schedule (daily at 00:05 local time):

```cron
5 0 * * * cd /Users/jay/.openclaw/workspace/pqts && /usr/bin/python3 scripts/daily_paper_ops.py >> logs/daily_paper_ops.log 2>&1
```

## Ops Health Report

Generate a standalone ops-health report from the latest campaign snapshot:

```bash
python3 scripts/ops_health_report.py \
  --reports-dir data/reports \
  --out-dir data/reports
```

## Performance Metrics

- **Total Return**: Overall strategy return
- **Sharpe Ratio**: Risk-adjusted return
- **Max Drawdown**: Peak-to-trough decline
- **Win Rate**: % of winning trades
- **Profit Factor**: Gross profit / gross loss
- **Total Trades**: Number of closed trades

## Example Results

```
Strategy: trend_following
Period: 2024-01-01 to 2024-03-31
Initial Capital: $10,000
Final Capital: $11,245

Total Return: 12.45%
Sharpe Ratio: 1.34
Max Drawdown: -8.20%
Win Rate: 58.3%
Profit Factor: 1.65
Total Trades: 42
```
