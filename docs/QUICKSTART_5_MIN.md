# 5-Minute Quickstart

## 1) Install + Initialize (Package-First Path)

```bash
pip install -U pqts
pqts quickstart --execute
```

This is the canonical beginner path. It creates a safe local workspace (`data/`, `results/`, `logs/`) and runs the guided first-success sequence.

Source/development fallback (advanced users):

```bash
git clone https://github.com/jakerslam/pqts.git
cd pqts
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pqts init
# fallback if console scripts are unavailable:
python main.py init
```

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

## 5) Primary Web Surface + Runtime Paths

Primary public web surface: Next.js (`apps/web`).
Dash fallback (operator/internal): `python src/dashboard/start.py`.

```bash
cd apps/web
npm install
npm run dev
# or run engine/runtime directly:
cd ..
python main.py run config/paper.yaml --show-toggles
# Dash fallback (operator/internal):
python src/dashboard/start.py
docker compose up --build
# optional Dash fallback in compose:
docker compose --profile operator up --build
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

## 8) Benchmark + Campaign Harnesses

```bash
# 90-day campaign harness
make paper-90d

# reference bundles + monthly benchmark report
make benchmark-program

# certified-paper integrations gate
make certified-paper
```
