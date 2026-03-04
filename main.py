# Protheus Quant Trading System
# Quick Start Script

import asyncio
import sys
import os
import argparse

from core.engine import TradingEngine
from core.toggle_manager import ToggleValidationError
from analytics.dashboard import AnalyticsDashboard

def _csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PQTS with runtime market/strategy toggles.")
    parser.add_argument(
        "config",
        nargs="?",
        default="config/paper.yaml",
        help="Path to YAML config (default: config/paper.yaml)",
    )
    parser.add_argument(
        "--profile",
        help="Strategy profile name from config.strategy_profiles",
    )
    parser.add_argument(
        "--markets",
        help="Comma-separated active markets (crypto, forex, equities).",
    )
    parser.add_argument(
        "--strategies",
        help="Comma-separated active strategy names.",
    )
    parser.add_argument(
        "--show-toggles",
        action="store_true",
        help="Print resolved toggle state and continue startup.",
    )
    return parser


def apply_cli_toggles(engine: TradingEngine, args: argparse.Namespace) -> None:
    if args.profile:
        engine.apply_strategy_profile(args.profile)
    if args.markets:
        engine.set_active_markets(_csv_list(args.markets))
    if args.strategies:
        engine.set_active_strategies(_csv_list(args.strategies))


async def main():
    """Main entry point"""
    args = build_arg_parser().parse_args()
    config_path = args.config

    print("=" * 60)
    print("  PROTHEUS QUANT TRADING SYSTEM (PQTS)")
    print("  Paper Trading Mode")
    print("=" * 60)

    if not os.path.exists(config_path):
        print(f"\n❌ Configuration file not found: {config_path}")
        print("\nCreate a config file or use:")
        print("  python main.py config/paper.yaml")
        sys.exit(1)
    
    # Initialize engine
    engine = TradingEngine(config_path)
    try:
        apply_cli_toggles(engine, args)
    except ToggleValidationError as exc:
        print(f"\n❌ Invalid toggle option: {exc}")
        sys.exit(2)

    toggle_state = engine.get_toggle_state()
    active_markets = toggle_state.get("active_markets", [])
    active_strategies = toggle_state.get("active_strategies", [])
    
    # Initialize dashboard
    dashboard = AnalyticsDashboard(engine.config.get('analytics', {}))
    
    try:
        print("\n🚀 Starting trading engine...")
        print("   Mode: Paper Trading")
        print(f"   Markets: {', '.join(active_markets) if active_markets else 'none'}")
        print(f"   Strategies: {', '.join(active_strategies) if active_strategies else 'none'}")
        if args.show_toggles:
            print(f"   Toggle State: {toggle_state}")
        print("\nPress Ctrl+C to stop\n")
        
        # Start engine
        await engine.start()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping trading engine...")
        await engine.stop()
        print("✅ Trading engine stopped")
        
        # Generate final report
        report = dashboard.generate_report()
        print("\n📊 Final Performance Report:")
        dashboard.print_dashboard()

if __name__ == "__main__":
    asyncio.run(main())
