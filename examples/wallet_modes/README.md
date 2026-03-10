# Wallet Mode Examples

This pack provides copy-run wallet-mode examples for integration onboarding.

## Setup

```bash
cp examples/wallet_modes/.env.example .env
```

## Read-Only Planning (No Secrets Required)

```bash
python3 examples/wallet_modes/run_example.py --mode eoa --dry-run --output json
python3 examples/wallet_modes/run_example.py --mode proxy --dry-run --output json
python3 examples/wallet_modes/run_example.py --mode safe --dry-run --output json
```

## Authenticated Readiness Checks

```bash
python3 examples/wallet_modes/run_example.py --mode eoa --output json
python3 examples/wallet_modes/run_example.py --mode proxy --output json
python3 examples/wallet_modes/run_example.py --mode safe --output json
```

Each command returns:
- required env vars
- missing env vars (if any)
- selected signature type contract
