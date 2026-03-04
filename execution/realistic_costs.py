"""
Realistic Execution Cost Model

Implements Grok's recommendation:
- Volume-based + volatility-adjusted slippage
- Square-root market impact law
- Maker-only optimization
- TWAP/POV slicing for large orders

Every 0.05% fee reduction on $100k at 5x turnover = +$2,500/year
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrderBook:
    """Simplified order book representation"""
    bids: List[Tuple[float, float]]  # (price, size)
    asks: List[Tuple[float, float]]
    spread: float
    best_bid: float
    best_ask: float
    mid_price: float
    
    @classmethod
    def from_snapshots(cls, bids: list, asks: list):
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2
        
        return cls(
            bids=bids,
            asks=asks,
            spread=spread,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid
        )
    
    def depth_at_price(self, price: float, side: str) -> float:
        """Get volume available at given price level"""
        levels = self.bids if side == 'buy' else self.asks
        total = 0
        for p, s in levels:
            if (side == 'buy' and p >= price) or (side == 'sell' and p <= price):
                total += s
        return total
    
    def depth_up_to_pct(self, pct: float) -> float:
        """Get USD depth within X% of mid price"""
        target_price = self.mid_price * (1 - pct)
        return self.depth_at_price(target_price, 'buy')


class RealisticCostModel:
    """
    Market impact model based on academic literature.
    
    References:
    - Almgren et al. (2005): square-root law
    - Bouchaud et al. (2002): order book dynamics
    """
    
    def __init__(self,
                 commission_rate: float = 0.001,  # 0.1% (maker rebate or taker fee)
                 base_volatility: float = 0.50,    # 50% annualized
                 impact_constant: float = 0.5):     # Empirical constant
        self.commission = commission_rate
        self.base_vol = base_volatility
        self.eta = impact_constant  # Market impact coefficient
        
        logger.info(f"Cost model: commission={commission:.3%}")
    
    def estimate_slippage(self,
                         order_size_usd: float,
                         order_book: OrderBook,
                         current_volatility: float,
                         is_market_order: bool = False) -> float:
        """
        Estimate slippage using square-root market impact law.
        
        Market impact = σ × √( participation )
        
        where:
        - σ = current volatility
        - participation = order_size / market_depth
        """
        # Market depth at 1% from mid
        depth = order_book.depth_up_to_pct(0.01)
        
        if depth == 0:
            # Thin market - high slippage
            return 0.01  # 1%
        
        participation = order_size_usd / depth
        
        # Temporary impact (what we pay immediately)
        temp_impact = self.eta * current_volatility * np.sqrt(participation)
        
        # Permanent impact (long-term price change)
        # Usually 10-20% of temporary
        permanent = temp_impact * 0.1
        
        total = temp_impact + permanent
        
        # Market orders pay approximately half the spread additionally
        if is_market_order:
            total += order_book.spread / order_book.mid_price / 2
        
        return total
    
    def get_execution_slices(self,
                           total_size: float,
                           order_book: OrderBook,
                           max_participation: float = 0.05) -> List[Dict]:
        """
        Split large orders to minimize market impact.
        
        Target: Each slice < 5% of market depth.
        """
        depth = order_book.depth_up_to_pct(0.01)
        max_slice = depth * max_participation
        
        n_slices = int(np.ceil(total_size / max_slice))
        base_slice = total_size / n_slices
        
        slices = []
        for i in range(n_slices):
            # Adjust final slice for rounding
            if i == n_slices - 1:
                slice_size = total_size - sum(s['size'] for s in slices)
            else:
                slice_size = base_slice
            
            slices.append({
                'size': slice_size,
                'delay_s': 10,  # 10 seconds between slices
                'type': 'passive',  # Post-only limit
                'est_impact': self.estimate_slippage(
                    slice_size, order_book, self.base_vol, is_market_order=False
                )
            })
        
        return slices
    
    def should_use_maker_only(self, order_book: OrderBook,
                             urgency: str = 'normal') -> bool:
        """
        Decide if we should use maker-only orders.
        
        Rules:
        - Wide spread (> 5x commission): Use maker
        - Normal urgency + spread > 2x commission: Use maker
        - High urgency + tight spread: Use market
        """
        spread_pct = order_book.spread / order_book.mid_price
        
        if urgency == 'urgent':
            return spread_pct < self.commission * 2
        
        # Normal urgency: prefer maker if spread justifies it
        return spread_pct > self.commission * 2
    
    def calculate_total_cost(self,
                           size: float,
                           price: float,
                           order_book: OrderBook = None,
                           volatility: float = None) -> Dict:
        """
        Calculate all transaction costs.
        """
        if volatility is None:
            volatility = self.base_vol
        
        if order_book:
            # Use realistic slippage
            slippage = self.estimate_slippage(
                size * price, order_book, volatility
            )
        else:
            # Fallback: 5 bps base
            slippage = 0.0005
        
        # Components
        commission_cost = size * price * self.commission
        slippage_cost = size * price * slippage
        
        return {
            'commission': commission_cost,
            'slippage': slippage_cost,
            'total_cost': commission_cost + slippage_cost,
            'total_cost_pct': (commission_cost + slippage_cost) / (size * price),
            'slippage_pct': slippage,
            'commission_pct': self.commission
        }


class TWAPExecutor:
    """
    Time-Weighted Average Price execution.
    
    Splits large orders to minimize market impact.
    Adapts slice sizes based on volume profile.
    """
    
    def __init__(self,
                 total_size: float,
                 duration_seconds: float,
                 min_slice_interval: float = 10):
        """
        Args:
            total_size: Total order size (units)
            duration_seconds: How long to distribute order
            min_slice_interval: Minimum seconds between slices
        """
        self.total_size = total_size
        self.duration = duration_seconds
        self.min_interval = min_slice_interval
        
        # Calculate number of slices
        self.n_slices = int(duration_seconds / min_slice_interval)
        self.completed = 0
        self.remaining = total_size
        
        # Volume profile (U-shaped: more volume at start/end)
        self.volume_profile = self._generate_volume_profile()
        
    def _generate_volume_profile(self) -> np.ndarray:
        """Generate U-shaped volume profile."""
        # More volume at start and end
        x = np.linspace(-1, 1, self.n_slices)
        profile = 1 + 0.5 * x**2  # U-shape
        return profile / profile.sum()  # Normalize to sum to 1
    
    def get_next_slice(self, order_book: OrderBook = None) -> Optional[Dict]:
        """
        Get next slice to execute.
        
        Returns None when complete.
        """
        if self.completed >= self.n_slices:
            return None
        
        # Size based on volume profile
        profile_pct = self.volume_profile[self.completed]
        slice_size = self.total_size * profile_pct
        
        # Adjust if we're at the last slice
        if self.completed == self.n_slices - 1:
            slice_size = self.remaining
        
        slice_info = {
            'slice_number': self.completed + 1,
            'total_slices': self.n_slices,
            'size': slice_size,
            'remaining_after': self.remaining - slice_size,
            'delay_next': self.min_interval,
            'volume_profile_weight': profile_pct,
            'aggression': 'passive'  # Always start passive
        }
        
        # Check if we should go aggressive
        if order_book:
            spread_pct = order_book.spread / order_book.mid_price
            if spread_pct < 0.0003:  # Very tight spread
                slice_info['aggression'] = 'market'
        
        self.completed += 1
        self.remaining -= slice_size
        
        return slice_info
    
    def get_progress(self) -> Dict:
        """Get execution progress."""
        return {
            'completed_slices': self.completed,
            'total_slices': self.n_slices,
            'completed_pct': self.completed / self.n_slices,
            'size_filled': self.total_size - self.remaining,
            'size_remaining': self.remaining,
            'estimated_completion': self.duration * (1 - self.completed / self.n_slices)
        }


class POVExecutor:
    """
    Percentage of Volume execution.
    
    Execute at a fixed participation rate of market volume.
    """
    
    def __init__(self,
                 total_size: float,
                 participation_rate: float = 0.05):  # 5% of volume
        """
        Args:
            total_size: Total order size
            participation_rate: Target % of market volume per period
        """
        self.total_size = total_size
        self.participation_rate = participation_rate
        self.filled = 0
        self.remaining = total_size
        
    def get_target_size(self, market_volume: float) -> float:
        """Get target size for next period based on market volume."""
        target = market_volume * self.participation_rate
        
        # Don't overshoot
        if self.filled + target > self.total_size:
            target = self.total_size - self.filled
        
        return target
    
    def update_filled(self, amount: float):
        """Record filled amount."""
        self.filled += amount
        self.remaining -= amount
    
    def is_complete(self) -> bool:
        """Check if order is complete."""
        return self.remaining <= 0.01  # Tolerance


class ExecutionOptimizer:
    """
    High-level optimizer that chooses execution method.
    """
    
    def __init__(self, cost_model: RealisticCostModel):
        self.cost_model = cost_model
        
    def optimize_execution(self,
                          order_size: float,
                          order_book: OrderBook,
                          urgency: str = 'normal',
                          max_impact: float = 0.001) -> Dict:
        """
        Choose optimal execution strategy.
        
        Returns execution plan.
        """
        # Estimate impact of single order
        single_impact = self.cost_model.estimate_slippage(
            order_size * order_book.mid_price,
            order_book,
            self.cost_model.base_vol
        )
        
        if single_impact <= max_impact or urgency == 'urgent':
            # Single order is fine or urgency demands it
            return {
                'method': 'single',
                'type': 'market' if urgency == 'urgent' else 'limit',
                'size': order_size,
                'est_impact': single_impact
            }
        
        # Need to split
        slices = self.cost_model.get_execution_slices(
            order_size, order_book, max_participation=0.05
        )
        
        total_impact = sum(s['est_impact'] * s['size'] for s in slices) / order_size
        
        if total_impact < single_impact * 0.7:  # Significant improvement
            return {
                'method': 'twap',
                'slices': slices,
                'duration': len(slices) * 10,
                'total_slices': len(slices),
                'est_impact': total_impact
            }
        
        # Single order better
        return {
            'method': 'single',
            'type': 'limit',
            'size': order_size,
            'est_impact': single_impact
        }


if __name__ == "__main__":
    # Test
    print("=" * 70)
    print("REALISTIC COST MODEL - TEST")
    print("=" * 70)
    
    # Create order book
    bids = [(100 - i*0.01, 1000 / (i+1)) for i in range(10)]
    asks = [(100 + i*0.01, 1000 / (i+1)) for i in range(10)]
    
    ob = OrderBook.from_snapshots(bids, asks)
    
    print(f"\nOrder Book:")
    print(f"  Best Bid: {ob.best_bid}")
    print(f"  Best Ask: {ob.best_ask}")
    print(f"  Spread: {ob.spread:.4f} ({ob.spread/ob.mid_price:.4%})")
    print(f"  Mid: {ob.mid_price}")
    
    # Cost model
    model = RealisticCostModel(
        commission_rate=0.001,  # 0.1%
        base_volatility=0.50,   # 50% annual vol
        impact_constant=0.5
    )
    
    # Test different order sizes
    sizes = [1000, 10000, 50000, 100000]
    
    print(f"\n{'='*70}")
    print("SLIPPAGE ESTIMATES:")
    print(f"{'='*70}")
    
    for size in sizes:
        impact = model.estimate_slippage(size, ob, 0.50)
        cost = model.calculate_total_cost(size, ob.mid_price, ob, 0.50)
        
        print(f"\nOrder: ${size:,.0f}")
        print(f"  Est. slippage: {impact:.4%}")
        print(f"  Commission:    ${cost['commission']:,.2f}")
        print(f"  Slippage:      ${cost['slippage']:,.2f}")
        print(f"  Total cost:    {cost['total_cost_pct']:.4%}")
        
        # Check if we should slice
        slices = model.get_execution_slices(size, ob)
        if len(slices) > 1:
            print(f"  Slicing:       {len(slices)} slices recommended")
    
    # TWAP
    print(f"\n{'='*70}")
    print("TWAP EXECUTION EXAMPLE:")
    print(f"{'='*70}")
    
    twap = TWAPExecutor(
        total_size=50000,
        duration_seconds=300,  # 5 minutes
        min_slice_interval=10
    )
    
    print(f"Total slices: {twap.n_slices}")
    print(f"Duration: {twap.duration}s")
    
    for i in range(min(3, twap.n_slices)):
        slice_info = twap.get_next_slice(ob)
        print(f"\nSlice {slice_info['slice_number']}:")
        print(f"  Size: ${slice_info['size']:,.2f}")
        print(f"  Weight: {slice_info['volume_profile_weight']:.3f}")
    
    print(f"\n{'='*70}")
    print("Cost model ready for realistic backtesting!")
    print("=" * 70)
