# Protheus Quant Trading System
# Quick Start Script

import asyncio
import sys
import os
from pathlib import Path

# Add pqts to path
sys.path.insert(0, str(Path(__file__).parent))

from core.engine import TradingEngine
from analytics.dashboard import AnalyticsDashboard

async def main():
    """Main entry point"""
    print("="*60)
    print("  PROTHEUS QUANT TRADING SYSTEM (PQTS)")
    print("  Paper Trading Mode")
    print("="*60)
    
    # Load configuration
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/paper.yaml"
    
    if not os.path.exists(config_path):
        print(f"\n❌ Configuration file not found: {config_path}")
        print("\nCreate a config file or use:")
        print("  python main.py config/paper.yaml")
        sys.exit(1)
    
    # Initialize engine
    engine = TradingEngine(config_path)
    
    # Initialize dashboard
    dashboard = AnalyticsDashboard(engine.config.get('analytics', {}))
    
    try:
        print("\n🚀 Starting trading engine...")
        print("   Mode: Paper Trading")
        print("   Markets: Crypto (Binance Testnet)")
        print("   Strategies: Scalping, Arbitrage, Trend, ML")
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
