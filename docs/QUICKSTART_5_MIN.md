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

## 4) Start Paper Campaign (Bounded)

```bash
pqts paper start
```

This runs a bounded paper campaign with risk-safe defaults and writes snapshots to `data/reports/paper`.

## 5) Legacy Runtime and Docker Paths

```bash
pqts run config/paper.yaml --show-toggles
docker compose up --build
```
