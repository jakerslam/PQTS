# 5-Minute Quickstart

## 1) Install + Initialize

```bash
pip install pqts
pqts init
```

This creates a safe local workspace (`data/`, `results/`, `logs/`) and copies `.env.example` when available.

## 2) Run a Meaningful Demo

```bash
pqts demo
```

This executes a fast deterministic simulation suite with safe defaults and writes outputs under `data/reports/demo`.

## 3) Run a Template Backtest

```bash
pqts backtest momentum
```

This runs a template-driven simulation/backtest flow and stores artifacts in `data/reports/backtest`.
Each run also emits:
- `template_run_<timestamp>.json`
- `template_run_diff_<timestamp>.diff`

## 4) Start Paper Campaign (Bounded)

```bash
pqts paper start
```

This runs a bounded paper campaign with risk-safe defaults and writes snapshots to `data/reports/paper`.
Paper-start also emits template artifacts/diffs for transparent GUI->code handoff.

## 5) Legacy Runtime and Docker Paths

```bash
pqts run config/paper.yaml --show-toggles
docker compose up --build
```

## 6) Read-Only First + Wallet Mode Progression

Read-only planning path (no wallet/secrets required):

```bash
python3 examples/wallet_modes/run_example.py --mode eoa --dry-run --output json
python3 examples/wallet_modes/run_example.py --mode proxy --dry-run --output json
python3 examples/wallet_modes/run_example.py --mode safe --dry-run --output json
```

Authenticated readiness checks (after env setup):

```bash
python3 examples/wallet_modes/run_example.py --mode eoa --output json
python3 examples/wallet_modes/run_example.py --mode proxy --output json
python3 examples/wallet_modes/run_example.py --mode safe --output json
```

## 7) Governance Gates (Recommended Before PR/Release)

```bash
make governance-check
```
