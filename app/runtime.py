"""Runtime entrypoint that wires CLI, composition root, and engine lifecycle."""

from __future__ import annotations

import os
import sys

from analytics.dashboard import AnalyticsDashboard
from app.bootstrap import bootstrap_runtime
from app.cli import apply_cli_toggles, build_arg_parser
from core.toggle_manager import ToggleValidationError


async def main(argv: list[str] | None = None) -> None:
    """Main async entrypoint."""

    args = build_arg_parser().parse_args(argv)
    config_path = args.config

    print("=" * 60)
    print("  PROTHEUS QUANT TRADING SYSTEM (PQTS)")
    print("  Paper Trading Mode")
    print("=" * 60)

    if not os.path.exists(config_path):
        print(f"\nConfiguration file not found: {config_path}")
        print("\nCreate a config file or use:")
        print("  python main.py config/paper.yaml")
        sys.exit(1)

    runtime_context, registry = bootstrap_runtime(config_path)
    engine = runtime_context.engine

    try:
        operator_tier = apply_cli_toggles(engine, args)
    except ToggleValidationError as exc:
        print(f"\nInvalid toggle option: {exc}")
        sys.exit(2)
    except ValueError as exc:
        print(f"\nInvalid operator tier option: {exc}")
        sys.exit(2)

    toggle_state = engine.get_toggle_state()
    active_markets = toggle_state.get("active_markets", [])
    active_strategies = toggle_state.get("active_strategies", [])

    dashboard = AnalyticsDashboard(engine.config.get("analytics", {}))

    modules_started = False
    try:
        print("\nStarting trading engine...")
        print("   Mode: Paper Trading")
        print(f"   Markets: {', '.join(active_markets) if active_markets else 'none'}")
        print(f"   Strategies: {', '.join(active_strategies) if active_strategies else 'none'}")
        print(f"   Operator Tier: {operator_tier}")
        print(
            "   Architecture Modules: "
            + ", ".join(registry.resolve_start_order())
        )
        if args.show_toggles:
            print(f"   Toggle State: {toggle_state}")
        print("\nPress Ctrl+C to stop\n")

        await registry.start_all(runtime_context)
        modules_started = True
        await engine.start()

    except KeyboardInterrupt:
        print("\n\nStopping trading engine...")
        await engine.stop()
        if modules_started:
            await registry.stop_all(runtime_context)
        print("Trading engine stopped")

        dashboard.generate_report()
        print("\nFinal Performance Report:")
        dashboard.print_dashboard()
    except Exception:
        if modules_started:
            await registry.stop_all(runtime_context)
        raise
