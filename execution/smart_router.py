# Smart Order Router
import logging
import asyncio
from collections.abc import Mapping
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"

@dataclass
class OrderRequest:
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # GTC, IOC, FOK

@dataclass
class RouteDecision:
    exchange: str
    order_type: OrderType
    price: Optional[float]
    split_orders: List[OrderRequest]
    expected_cost: float
    expected_slippage: float

class SmartOrderRouter:
    """
    Intelligent order routing to minimize costs and slippage.
    
    Features:
    - Exchange selection based on liquidity/fees
    - Order type optimization
    - Large order splitting (TWAP/VWAP)
    - Maker vs taker decision
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.max_single_order_size = config.get('max_single_order_size', 1.0)  # BTC
        self.twap_interval_seconds = config.get('twap_interval_seconds', 60)
        self.prefer_maker = config.get('prefer_maker', True)
        
        # Exchange configs
        self.exchanges = config.get('exchanges', {})
        
        logger.info(f"SmartOrderRouter initialized")
    
    async def route_order(self, request: OrderRequest, 
                         market_data: Dict) -> RouteDecision:
        """Determine optimal routing for order"""
        
        # Select best exchange
        exchange = self._select_exchange(request.symbol, market_data)
        
        # Determine order type
        order_type = self._select_order_type(request, market_data)
        
        # Split large orders
        split_orders = self._split_order(request, market_data)
        
        # Calculate costs
        expected_cost, expected_slippage = self._estimate_costs(
            request, exchange, order_type, market_data
        )
        
        # Optimize price
        price = self._optimize_price(request, order_type, market_data)
        
        return RouteDecision(
            exchange=exchange,
            order_type=order_type,
            price=price,
            split_orders=split_orders,
            expected_cost=expected_cost,
            expected_slippage=expected_slippage
        )

    def _iter_exchange_views(self, market_data: Dict) -> List[Tuple[str, Dict]]:
        """
        Yield normalized exchange -> symbol quote maps.

        Market snapshots can include scalar metadata keys such as
        `last_price`/`vol_24h` plus nested order book payloads. These are
        ignored here to keep routing deterministic and robust.
        """
        views: List[Tuple[str, Dict]] = []
        for exchange, payload in market_data.items():
            if not isinstance(payload, Mapping):
                continue
            if exchange == "order_book":
                continue
            if any(isinstance(v, Mapping) and "price" in v for v in payload.values()):
                views.append((exchange, dict(payload)))
        return views
    
    def _select_exchange(self, symbol: str, market_data: Dict) -> str:
        """Select best exchange for symbol"""
        best_exchange = None
        best_score = -1
        
        for exchange, data in self._iter_exchange_views(market_data):
            if symbol not in data:
                continue
            
            symbol_data = data[symbol]
            
            # Score based on:
            # 1. Liquidity (bid/ask spread)
            spread = symbol_data.get('spread', 0.01)
            spread_score = 1 / (1 + spread * 100)
            
            # 2. Volume
            volume = symbol_data.get('volume_24h', 0)
            volume_score = min(volume / 1000000, 1.0)  # Normalize to 1M
            
            # 3. Fees
            maker_fee = self.exchanges.get(exchange, {}).get('maker_fee', 0.001)
            fee_score = 1 / (1 + maker_fee * 1000)
            
            # Combined score
            score = spread_score * 0.4 + volume_score * 0.4 + fee_score * 0.2
            
            if score > best_score:
                best_score = score
                best_exchange = exchange
        
        return best_exchange or 'binance'
    
    def _select_order_type(self, request: OrderRequest, market_data: Dict) -> OrderType:
        """Select optimal order type"""
        
        # Large orders: use TWAP
        if request.quantity > self.max_single_order_size:
            return OrderType.TWAP
        
        # If we can get filled as maker, use limit
        if self.prefer_maker and request.price:
            current_price = self._get_current_price(request.symbol, market_data)
            
            if request.side == 'buy' and request.price < current_price:
                return OrderType.LIMIT
            elif request.side == 'sell' and request.price > current_price:
                return OrderType.LIMIT
        
        # Urgent execution: market order
        if request.time_in_force == 'IOC':
            return OrderType.MARKET
        
        return OrderType.LIMIT
    
    def _split_order(self, request: OrderRequest, market_data: Dict) -> List[OrderRequest]:
        """Split large orders for optimal execution"""
        
        if request.quantity <= self.max_single_order_size:
            return [request]
        
        # TWAP splitting
        num_slices = int(request.quantity / self.max_single_order_size) + 1
        slice_size = request.quantity / num_slices
        
        splits = []
        for i in range(num_slices):
            split = OrderRequest(
                symbol=request.symbol,
                side=request.side,
                quantity=slice_size,
                order_type=OrderType.LIMIT,
                price=request.price,
                time_in_force=request.time_in_force
            )
            splits.append(split)
        
        return splits
    
    def _estimate_costs(self, request: OrderRequest, exchange: str,
                       order_type: OrderType, market_data: Dict) -> tuple:
        """Estimate trading costs"""
        
        exchange_config = self.exchanges.get(exchange, {})
        
        if order_type == OrderType.LIMIT:
            fee = exchange_config.get('maker_fee', 0.001)
            slippage = 0.0001  # Minimal for maker
        else:
            fee = exchange_config.get('taker_fee', 0.001)
            slippage = 0.001  # Higher for taker
        
        # Adjust for order size
        size_factor = min(request.quantity / 10, 1.0)  # Larger = more slippage
        slippage *= (1 + size_factor)
        
        notional = request.quantity * (request.price or self._get_current_price(request.symbol, market_data))
        expected_cost = notional * fee
        expected_slippage = notional * slippage
        
        return expected_cost, expected_slippage
    
    def _optimize_price(self, request: OrderRequest, order_type: OrderType,
                       market_data: Dict) -> Optional[float]:
        """Optimize order price for best execution"""
        
        if order_type == OrderType.MARKET:
            return None
        
        current_price = self._get_current_price(request.symbol, market_data)
        
        if not current_price:
            return request.price
        
        # Add small buffer for better fill probability
        if request.side == 'buy':
            # Bid slightly above to get maker fill
            return current_price * 0.9995
        else:
            # Ask slightly below
            return current_price * 1.0005
    
    def _get_current_price(self, symbol: str, market_data: Dict) -> Optional[float]:
        """Get current market price"""
        for _, exchange_data in self._iter_exchange_views(market_data):
            if symbol in exchange_data:
                return exchange_data[symbol].get('price')
        return None
    
    async def execute_route(self, decision: RouteDecision) -> bool:
        """Execute the routing decision"""
        logger.info(f"Executing route: {decision.exchange}, {decision.order_type.value}")
        
        try:
            if decision.order_type == OrderType.TWAP:
                # Execute TWAP over time
                for i, order in enumerate(decision.split_orders):
                    if i > 0:
                        await asyncio.sleep(self.twap_interval_seconds)
                    
                    logger.info(f"TWAP slice {i+1}/{len(decision.split_orders)}: {order.quantity}")
                    # Execute order...
            else:
                # Execute single order
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Route execution failed: {e}")
            return False
