# Core Trading Engine
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketType(Enum):
    CRYPTO = "crypto"
    EQUITIES = "equities"
    FOREX = "forex"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    market: MarketType = MarketType.CRYPTO
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0

@dataclass
class Position:
    symbol: str
    quantity: float
    avg_entry_price: float
    market: MarketType
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class MarketData:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    market: MarketType
    bid: Optional[float] = None
    ask: Optional[float] = None
    
class TradingEngine:
    """Main trading execution engine"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.mode = self.config.get('mode', 'paper_trading')
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.strategies: List[Any] = []
        self.risk_manager = None
        self.portfolio_manager = None
        self.running = False
        
        logger.info(f"TradingEngine initialized in {self.mode} mode")
    
    def _load_config(self, path: str) -> dict:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    async def start(self):
        """Start the trading engine"""
        logger.info("Starting trading engine...")
        self.running = True
        
        # Initialize market adapters
        await self._init_markets()
        
        # Initialize risk manager
        await self._init_risk_manager()
        
        # Initialize strategies
        await self._init_strategies()
        
        # Start main loop
        await self._main_loop()
    
    async def _init_markets(self):
        """Initialize market adapters"""
        markets_config = self.config.get('markets', {})
        
        if markets_config.get('crypto', {}).get('enabled'):
            logger.info("Initializing crypto markets...")
            # Initialize crypto adapters
            
        if markets_config.get('equities', {}).get('enabled'):
            logger.info("Initializing equity markets...")
            # Initialize equity adapters
            
        if markets_config.get('forex', {}).get('enabled'):
            logger.info("Initializing forex markets...")
            # Initialize forex adapters
    
    async def _init_risk_manager(self):
        """Initialize risk management"""
        from .risk_manager import RiskManager
        self.risk_manager = RiskManager(self.config.get('risk', {}))
        logger.info("Risk manager initialized")
    
    async def _init_strategies(self):
        """Initialize trading strategies"""
        strategies_config = self.config.get('strategies', {})
        
        for strategy_name, config in strategies_config.items():
            if config.get('enabled', False):
                logger.info(f"Initializing strategy: {strategy_name}")
                # Load strategy dynamically
    
    async def _main_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                # Update market data
                await self._update_market_data()
                
                # Run strategies
                await self._run_strategies()
                
                # Check risk limits
                await self._check_risk_limits()
                
                # Sleep for tick interval
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)
    
    async def _update_market_data(self):
        """Fetch latest market data"""
        pass
    
    async def _run_strategies(self):
        """Execute trading strategies"""
        for strategy in self.strategies:
            try:
                signals = await strategy.generate_signals(self.market_data)
                for signal in signals:
                    await self._process_signal(signal)
            except Exception as e:
                logger.error(f"Strategy error: {e}")
    
    async def _process_signal(self, signal: dict):
        """Process trading signal"""
        # Check risk limits
        if not await self.risk_manager.check_signal(signal):
            return
        
        # Create order
        order = Order(
            id=self._generate_order_id(),
            symbol=signal['symbol'],
            side=OrderSide(signal['side']),
            order_type=OrderType(signal.get('order_type', 'market')),
            quantity=signal['quantity'],
            price=signal.get('price'),
            market=MarketType(signal['market'])
        )
        
        # Submit order
        await self._submit_order(order)
    
    async def _submit_order(self, order: Order):
        """Submit order to market"""
        logger.info(f"Submitting order: {order}")
        self.orders[order.id] = order
        # Submit to appropriate market adapter
    
    async def _check_risk_limits(self):
        """Check and enforce risk limits"""
        if self.risk_manager:
            await self.risk_manager.check_limits(self.positions, self.orders)
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    async def stop(self):
        """Stop the trading engine"""
        logger.info("Stopping trading engine...")
        self.running = False
        # Close all positions
        # Cancel pending orders
        # Save state

if __name__ == "__main__":
    import sys
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/paper.yaml"
    engine = TradingEngine(config_path)
    
    try:
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        asyncio.run(engine.stop())
