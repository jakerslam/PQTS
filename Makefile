SHELL := /bin/bash
PYTHON ?= python3
VENV ?= .venv
VENV_PY := $(VENV)/bin/python

.PHONY: setup setup-lock demo test lint clean

setup:
	bash scripts/bootstrap_env.sh --python "$(PYTHON)" --venv "$(VENV)"

setup-lock:
	bash scripts/bootstrap_env.sh --python "$(PYTHON)" --venv "$(VENV)" --lock

demo:
	$(VENV_PY) demo.py --market crypto --strat ml-ensemble --source make_demo

test:
	$(VENV_PY) -m pytest -q

lint:
	$(VENV_PY) -m black --check core execution risk analytics markets demo.py
	$(VENV_PY) -m isort --check-only core execution risk analytics markets demo.py
	$(VENV_PY) -m ruff check core execution risk analytics markets --select E9,F63,F7,F82
	$(VENV_PY) -m flake8 core execution risk analytics markets --count --select=E9,F63,F7,F82 --show-source --statistics

clean:
	rm -rf "$(VENV)"

