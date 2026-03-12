SHELL := /bin/bash
PYTHON ?= python3
VENV ?= .venv
VENV_PY := $(VENV)/bin/python
PY_RUN := $(if $(wildcard $(VENV_PY)),$(VENV_PY),$(PYTHON))

.PHONY: setup setup-lock demo sim-suite stream-worker ws-ingestion tournament canary-ramp reconcile slo-report error-budget control-plane arch-check arch-map scaffold-module leaderboard-site codex-enforcer assimilation-66-71-check unmapped-srs-check full-srs-check dod-audit code-only-audit governance-check trust-surface-suite paper-6m paper-90d nightly-review run-mode native bench-exec reference-bundles reference-performance certified-paper chaos-suite benchmark-program docker-up observability-up doctor onboard status test lint clean

setup:
	bash scripts/bootstrap_env.sh --python "$(PYTHON)" --venv "$(VENV)"

setup-lock:
	bash scripts/bootstrap_env.sh --python "$(PYTHON)" --venv "$(VENV)" --lock

demo:
	$(VENV_PY) apps/demo.py --market crypto --strat ml-ensemble --source make_demo

doctor:
	$(VENV_PY) main.py doctor --fix

onboard:
	$(VENV_PY) main.py quickstart --execute

status:
	$(VENV_PY) main.py status reports
	$(VENV_PY) main.py status leaderboard
	$(VENV_PY) main.py status readiness

sim-suite:
	$(VENV_PY) scripts/run_simulation_suite.py --markets crypto,equities,forex --strategies market_making,funding_arbitrage,cross_exchange --cycles-per-scenario 60 --readiness-every 20

stream-worker:
	$(VENV_PY) scripts/run_shadow_stream_worker.py --cycles 10 --sleep-seconds 1.0

ws-ingestion:
	$(VENV_PY) scripts/run_ws_ingestion.py --cycles 30 --sleep-seconds 1.0

tournament:
	$(VENV_PY) scripts/run_strategy_tournament.py --start 2026-01-01T00:00:00Z --end 2026-02-01T00:00:00Z

canary-ramp:
	$(VENV_PY) scripts/run_canary_ramp.py

reconcile:
	$(VENV_PY) scripts/run_reconciliation_daemon.py --cycles 10 --sleep-seconds 5.0 --halt-on-mismatch

slo-report:
	$(VENV_PY) scripts/slo_health_report.py

error-budget:
	$(VENV_PY) scripts/weekly_error_budget_review.py --window-days 7

control-plane:
	$(VENV_PY) scripts/control_plane_report.py

arch-check:
	$(VENV_PY) tools/check_architecture_boundaries.py

arch-map:
	$(VENV_PY) tools/print_architecture_map.py

scaffold-module:
	@echo "Usage: make scaffold-module NAME=<module_name> REQUIRES=<a,b> PROVIDES=<x,y>"
	$(VENV_PY) tools/scaffold_module.py "$(NAME)" --requires "$(REQUIRES)" --provides "$(PROVIDES)"

leaderboard-site:
	$(VENV_PY) scripts/export_simulation_leaderboard_site.py --reports-dir data/reports --output-dir site

governance-check:
	$(PY_RUN) tools/check_codex_enforcer.py
	$(PY_RUN) tools/check_assimilation_66_71_defaults.py --config config/strategy/assimilation_66_71_defaults.json
	$(PY_RUN) tools/check_unmapped_srs_closure.py --defaults config/strategy/assimilation_unmapped_p2_defaults.json --todo docs/TODO.md --map docs/SRS_UNMAPPED_P2_EXECUTION_MAP.md
	$(PY_RUN) tools/check_full_srs_closure.py --defaults config/strategy/assimilation_full_closure_defaults.json --todo docs/TODO.md --map docs/SRS_FULL_CLOSURE_EXECUTION_MAP.md --srs docs/SRS.md
	$(PY_RUN) tools/check_truth_surface.py
	$(PY_RUN) tools/check_studio_contract.py
	$(PY_RUN) tools/check_core_professional_contract.py
	$(PY_RUN) tools/check_surface_contracts.py
	$(PY_RUN) tools/check_web_api_contracts.py
	$(PY_RUN) tools/check_scope_governance.py --requested-markets crypto
	$(PY_RUN) tools/check_integration_claim_parity.py --readme README.md --index config/integrations/official_integrations.json
	$(PY_RUN) scripts/run_exchange_certification.py --venues binance,coinbase,alpaca,oanda --output data/reports/certifications/latest.json
	$(PY_RUN) tools/check_certified_paper_integrations.py --index config/integrations/official_integrations.json --cert-report data/reports/certifications/latest.json
	$(PY_RUN) tools/check_native_latency_regression.py --results-dir results/native_benchmarks --policy config/native/latency_policy.json
	$(PY_RUN) tools/check_benchmark_program.py --reference-performance results/reference_performance_latest.json --results-root . --policy config/benchmarks/program_policy.json
	$(PY_RUN) tools/check_reference_performance_contract.py --reference-performance results/reference_performance_latest.json
	$(PY_RUN) tools/check_external_validation_evidence.py --user-research docs/USER_RESEARCH_2026_03.md --readme README.md
	$(PY_RUN) tools/check_external_beta_framework.py --registry data/validation/external_beta/cohort_registry.json --user-research docs/USER_RESEARCH_2026_03.md
	$(PY_RUN) tools/check_tier_safety_policy.py
	$(PY_RUN) tools/check_source_reliability.py
	$(PY_RUN) tools/check_roadmap_governance.py

trust-surface-suite:
	$(PY_RUN) tools/run_trust_surface_suite.py --out data/reports/validation/trust_surface_latest.json

codex-enforcer:
	$(PY_RUN) tools/check_codex_enforcer.py

top100-roi:
	$(PY_RUN) tools/generate_top_roi_moves.py --todo docs/TODO.md --top 100 --md-out docs/TOP_100_ROI_MOVES.md --json-out docs/TOP_100_ROI_MOVES.json

release-examples-check:
	$(PY_RUN) tools/check_release_examples.py --pyproject pyproject.toml --files README.md docs/RELEASE_CHECKLIST.md docs/QUICKSTART_5_MIN.md

claim-evidence-links-check:
	$(PY_RUN) tools/check_claim_evidence_links.py --target README.md --target docs/BENCHMARKS.md --target docs/REFERENCE_PERFORMANCE.md

assimilation-66-71-check:
	$(PY_RUN) tools/check_assimilation_66_71_defaults.py --config config/strategy/assimilation_66_71_defaults.json

unmapped-srs-check:
	$(PY_RUN) tools/check_unmapped_srs_closure.py --defaults config/strategy/assimilation_unmapped_p2_defaults.json --todo docs/TODO.md --map docs/SRS_UNMAPPED_P2_EXECUTION_MAP.md

dod-audit:
	$(PY_RUN) tools/generate_srs_coverage_matrix.py --srs docs/SRS.md --todo docs/TODO.md --json-out data/reports/srs_coverage/srs_coverage.json --md-out docs/SRS_COVERAGE_MATRIX.md
	$(PY_RUN) tools/audit_todo_dod.py --todo docs/TODO.md --coverage data/reports/srs_coverage/srs_coverage.json
	$(PY_RUN) tools/generate_srs_coverage_matrix.py --srs docs/SRS.md --todo docs/TODO.md --json-out data/reports/srs_coverage/srs_coverage.json --md-out docs/SRS_COVERAGE_MATRIX.md
	$(PY_RUN) tools/generate_srs_gap_backlog.py --srs docs/SRS.md --todo docs/TODO.md --out docs/SRS_GAP_BACKLOG.md
	$(PY_RUN) tools/check_codex_enforcer.py
	$(PY_RUN) tools/check_release_examples.py --pyproject pyproject.toml --files README.md docs/RELEASE_CHECKLIST.md docs/QUICKSTART_5_MIN.md
	$(PY_RUN) tools/generate_top_roi_moves.py --todo docs/TODO.md --top 100 --md-out docs/TOP_100_ROI_MOVES.md --json-out docs/TOP_100_ROI_MOVES.json
	$(PY_RUN) tools/check_assimilation_66_71_defaults.py --config config/strategy/assimilation_66_71_defaults.json
	$(PY_RUN) tools/check_unmapped_srs_closure.py --defaults config/strategy/assimilation_unmapped_p2_defaults.json --todo docs/TODO.md --map docs/SRS_UNMAPPED_P2_EXECUTION_MAP.md
	$(PY_RUN) tools/check_full_srs_closure.py --defaults config/strategy/assimilation_full_closure_defaults.json --todo docs/TODO.md --map docs/SRS_FULL_CLOSURE_EXECUTION_MAP.md --srs docs/SRS.md

full-srs-check:
	$(PY_RUN) tools/generate_full_srs_closure_artifacts.py --todo docs/TODO.md --defaults-out config/strategy/assimilation_full_closure_defaults.json --map-out docs/SRS_FULL_CLOSURE_EXECUTION_MAP.md
	$(PY_RUN) tools/check_full_srs_closure.py --defaults config/strategy/assimilation_full_closure_defaults.json --todo docs/TODO.md --map docs/SRS_FULL_CLOSURE_EXECUTION_MAP.md --srs docs/SRS.md

code-only-audit:
	$(PY_RUN) tools/audit_todo_code_only.py --todo docs/TODO.md --repo-root .
	$(PY_RUN) tools/generate_srs_coverage_matrix.py --srs docs/SRS.md --todo docs/TODO.md --json-out data/reports/srs_coverage/srs_coverage.json --md-out docs/SRS_COVERAGE_MATRIX.md
	$(PY_RUN) tools/generate_srs_gap_backlog.py --srs docs/SRS.md --todo docs/TODO.md --out docs/SRS_GAP_BACKLOG.md

paper-6m:
	$(VENV_PY) scripts/run_paper_6m_harness.py --months 6 --cycles-per-month 12 --sleep-seconds 0 --risk-profile balanced

paper-90d:
	$(PY_RUN) scripts/run_paper_90d_harness.py --days 90 --cycles-per-month 12 --sleep-seconds 0 --risk-profile balanced

nightly-review:
	$(VENV_PY) scripts/run_nightly_strategy_review.py --snapshot auto --output table

run-mode:
	$(VENV_PY) scripts/run_mode_entrypoint.py --print-plan

native:
	$(PY_RUN) -m pip install maturin
	$(PY_RUN) -m maturin build --manifest-path native/hotpath/Cargo.toml --release -i $(PY_RUN)
	$(PY_RUN) -m pip install --force-reinstall native/hotpath/target/wheels/pqts_hotpath-*.whl

bench-exec:
	$(PY_RUN) scripts/benchmark_execution_latency.py --orders 500 --target-p95-ms 200 --out-dir results/native_benchmarks

reference-bundles:
	$(PY_RUN) scripts/publish_reference_bundles.py --config config/paper.yaml --out-root results
	$(PY_RUN) scripts/render_reference_performance.py

reference-performance:
	$(PY_RUN) scripts/render_reference_performance.py

certified-paper:
	$(PY_RUN) scripts/run_exchange_certification.py --venues binance,coinbase,alpaca,oanda --output data/reports/certifications/latest.json
	$(PY_RUN) tools/check_certified_paper_integrations.py --index config/integrations/official_integrations.json --cert-report data/reports/certifications/latest.json

chaos-suite:
	$(PY_RUN) scripts/run_chaos_recovery_suite.py --strict --out-dir data/reports/chaos

benchmark-program:
	$(PY_RUN) scripts/publish_reference_bundles.py --config config/paper.yaml --out-root results
	$(PY_RUN) scripts/render_reference_performance.py
	$(PY_RUN) scripts/generate_monthly_report.py --results-dir results --out-dir data/reports/monthly
	$(PY_RUN) tools/check_benchmark_program.py --reference-performance results/reference_performance_latest.json --results-root . --policy config/benchmarks/program_policy.json --report-out data/reports/benchmark_program/latest.json

docker-up:
	docker compose up --build

observability-up:
	docker compose --profile observability up --build

test:
	$(VENV_PY) -m pytest -q

lint:
	$(VENV_PY) -m black --check src/core src/execution src/risk src/analytics src/markets apps/demo.py
	$(VENV_PY) -m isort --check-only src/core src/execution src/risk src/analytics src/markets apps/demo.py
	$(VENV_PY) -m ruff check src/core src/execution src/risk src/analytics src/markets --select E9,F63,F7,F82
	$(VENV_PY) -m flake8 src/core src/execution src/risk src/analytics src/markets --count --select=E9,F63,F7,F82 --show-source --statistics

clean:
	rm -rf "$(VENV)" .pytest_cache .mypy_cache .ruff_cache build dist site
	find src tests scripts tools -type d -name "__pycache__" -prune -exec rm -rf {} +
	find src -maxdepth 2 -type d -name "*.egg-info" -prune -exec rm -rf {} +
