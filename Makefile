SHELL := /bin/bash
PYTHON ?= python3
VENV ?= .venv
VENV_PY := $(VENV)/bin/python

.PHONY: setup setup-lock demo sim-suite stream-worker ws-ingestion tournament canary-ramp reconcile slo-report error-budget control-plane arch-check arch-map scaffold-module leaderboard-site governance-check docker-up test lint clean

setup:
	bash scripts/bootstrap_env.sh --python "$(PYTHON)" --venv "$(VENV)"

setup-lock:
	bash scripts/bootstrap_env.sh --python "$(PYTHON)" --venv "$(VENV)" --lock

demo:
	$(VENV_PY) apps/demo.py --market crypto --strat ml-ensemble --source make_demo

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
	$(VENV_PY) tools/check_studio_contract.py
	$(VENV_PY) tools/check_core_professional_contract.py
	$(VENV_PY) tools/check_scope_governance.py --requested-markets crypto
	$(VENV_PY) tools/check_tier_safety_policy.py
	$(VENV_PY) tools/check_source_reliability.py
	$(VENV_PY) tools/check_roadmap_governance.py

docker-up:
	docker compose up --build

test:
	$(VENV_PY) -m pytest -q

lint:
	$(VENV_PY) -m black --check src/core src/execution src/risk src/analytics src/markets apps/demo.py
	$(VENV_PY) -m isort --check-only src/core src/execution src/risk src/analytics src/markets apps/demo.py
	$(VENV_PY) -m ruff check src/core src/execution src/risk src/analytics src/markets --select E9,F63,F7,F82
	$(VENV_PY) -m flake8 src/core src/execution src/risk src/analytics src/markets --count --select=E9,F63,F7,F82 --show-source --statistics

clean:
	rm -rf "$(VENV)"
