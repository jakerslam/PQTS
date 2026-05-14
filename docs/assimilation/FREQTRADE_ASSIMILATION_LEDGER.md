# Freqtrade Assimilation Ledger

This is a work ledger for studying the cloned Freqtrade repository without importing its execution path into PQTS.

## Source Snapshot

- Source repo: `freqtrade/freqtrade`
- Source origin: `https://github.com/freqtrade/freqtrade.git`
- Source commit: `e00a1fd28c03`
- Generated at: `2026-05-14T00:50:10.573640+00:00`
- Tracked files: `773`
- CSV ledger: [freqtrade_file_ledger.csv](freqtrade_file_ledger.csv)
- JSON ledger: [freqtrade_file_ledger.json](freqtrade_file_ledger.json)

## Safety Boundary

- Treat Freqtrade as GPL-3.0 study material unless a deliberate license decision says otherwise.
- Do not copy Freqtrade source into PQTS.
- Assimilate behavior as PQTS-native designs, tests, contracts, and docs.
- External code must never submit orders or bypass `execution.RiskAwareRouter.submit_order()`.
- Any assimilated feature must pass PQTS OOS, walk-forward, deflated-Sharpe, cost, promotion, and kill-switch gates.

## Review Phases

| Phase | Meaning | Files |
| --- | --- | ---: |
| `P0` | Immediate assimilation candidates: strategy API, backtesting, protection, repo metadata | 137 |
| `P1` | High-value research/data patterns: hyperopt, FreqAI, exchange/data ingestion | 141 |
| `P2` | Control surfaces, persistence, and behavior-rich test coverage | 235 |
| `P3` | Documentation, build, release, and operator ergonomics | 127 |
| `P4` | Remaining triage | 133 |

## Category Counts

| Category | Files |
| --- | ---: |
| `backtesting_validation` | 68 |
| `build_release_ops` | 39 |
| `documentation` | 88 |
| `hyperopt_ml` | 96 |
| `market_data_exchange` | 45 |
| `ops_control_surface` | 54 |
| `other` | 133 |
| `persistence_analysis` | 16 |
| `repo_metadata` | 14 |
| `risk_protection` | 12 |
| `strategy_interface` | 43 |
| `test_suite` | 165 |

## High-Priority File Queue

Use the CSV/JSON ledgers for the exhaustive list. This queue shows the first high-priority files to work through.

| Phase | Category | File | PQTS target | Status |
| --- | --- | --- | --- | --- |
| `P0` | `backtesting_validation` | `docs/advanced-backtesting.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/assets/freqUI-backtesting-dark.png` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/assets/freqUI-backtesting-light.png` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/backtesting.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/commands/backtesting-analysis.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/commands/backtesting-show.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/commands/backtesting.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/commands/lookahead-analysis.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/commands/recursive-analysis.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/lookahead-analysis.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `docs/recursive-analysis.md` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/enums/backteststate.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/ft_types/backtest_result_type.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/__init__.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/analysis/__init__.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/analysis/base_analysis.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/analysis/lookahead.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/analysis/lookahead_helpers.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/analysis/recursive.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/analysis/recursive_helpers.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/backtest_caching.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/backtesting.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/bt_progress.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt/__init__.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt/hyperopt.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt/hyperopt_auto.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt/hyperopt_interface.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt/hyperopt_logger.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt/hyperopt_optimizer.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt/hyperopt_output.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_epoch_filters.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_calmar.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_interface.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_max_drawdown.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_max_drawdown_per_pair.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_max_drawdown_relative.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_multi_metric.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_onlyprofit.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_profit_drawdown.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_sharpe.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_sharpe_daily.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_short_trade_dur.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_sortino.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_loss/hyperopt_loss_sortino_daily.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/hyperopt_tools.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/optimize_reports/__init__.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/optimize_reports/bt_output.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/optimize_reports/bt_storage.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/optimize_reports/optimize_reports.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/space/__init__.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/space/decimalspace.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/optimize/space/optunaspaces.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `freqtrade/rpc/api_server/api_backtest.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/freqai/test_freqai_backtesting.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/optimize/test_backtest_detail.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/optimize/test_backtesting.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/optimize/test_backtesting_adjust_position.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/optimize/test_lookahead_analysis.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/optimize/test_recursive_analysis.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/strategy/strats/lookahead_bias/strategy_test_v3_with_lookahead_bias.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/strategy/strats/strategy_test_v3_recursive_issue.py` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/testdata/backtest_results/.last_result.json` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/testdata/backtest_results/backtest-result.json` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/testdata/backtest_results/backtest-result.meta.json` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/testdata/backtest_results/backtest-result_multistrat.json` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/testdata/backtest_results/backtest-result_multistrat.meta.json` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `tests/testdata/testconfigs/recursive.json` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `backtesting_validation` | `user_data/backtest_results/.gitkeep` | `src/research + scripts/run_real_money_validation.py` | `unreviewed` |
| `P0` | `repo_metadata` | `CONTRIBUTING.md` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `LICENSE` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `README.md` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `config_examples/config_binance.example.json` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `config_examples/config_freqai.example.json` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `config_examples/config_full.example.json` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `config_examples/config_kraken.example.json` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `pyproject.toml` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `requirements-dev.txt` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `requirements-freqai-rl.txt` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `requirements-freqai.txt` | `docs/assimilation + dependency policy` | `unreviewed` |
| `P0` | `repo_metadata` | `requirements-hyperopt.txt` | `docs/assimilation + dependency policy` | `unreviewed` |

## Ledger Columns

- `review_status`: `unreviewed`, `reading`, `mapped`, `implemented`, `rejected`, or `blocked`.
- `assimilation_decision`: `pending`, `study_only`, `pqts_native_candidate`, `implemented`, `rejected_license`, or `not_relevant`.
- `pqts_target`: the PQTS area likely to receive any native implementation.
- `license_boundary`: default legal/safety boundary for the file.

## Suggested Workflow

1. Start with `P0` rows in the CSV.
2. Read the external file and write a short finding in `notes` or a follow-up assimilation memo.
3. Decide `study_only`, `pqts_native_candidate`, or `not_relevant`.
4. Implement only PQTS-native behavior with new tests and promotion gates.
5. Preserve router-only execution and never instantiate external adapters in live paths.
