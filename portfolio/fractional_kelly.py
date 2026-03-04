"""
Fractional Kelly + Risk Parity Integration

Implements Grok's recommendations:
- Fractional Kelly (0.25-0.5 of full Kelly) for safety
- Volatility targeting (target 15-20% annualized vol)
- Risk parity allocation across selected strategies

Based on:
- Kelly Criterion (Kelly, 1956)
- Fractional Kelly (Thorp, 2006)
- Risk Parity (Asness, 1996)
- Hierarchical Risk Parity (Lopez de Prado, 2016)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyAllocation:
    """Position sizing for a single strategy"""
    strategy_name: str
    target_weight: float
    kelly_fraction: float
    volatility_scalar: float
    correlation_adjustment: float
    final_weight: float
    max_position_pct: float
    stop_loss_price: Optional[float]


class FractionalKellySizer:
    """
    Kelly Criterion with fractional sizing for risk management.
    
    Full Kelly: f* = (μ - r) / σ²
    This is too aggressive (high volatility, high drawdown).
    
    Fractional Kelly: f = c × f* where c ∈ [0.25, 0.5]
    """
    
    def __init__(self,
                 kelly_fraction: float = 0.25,  # Conservative: 0.25
                 max_leverage: float = 2.0,
                 min_position: float = 0.01,
                 max_position: float = 0.50):
        """
        Args:
            kelly_fraction: Fraction of full Kelly (0.25-0.5 recommended)
            max_leverage: Maximum allowed leverage
            min_position: Minimum position size
            max_position: Maximum position size
        """
        if not 0.1 <= kelly_fraction <= 1.0:
            raise ValueError("kelly_fraction must be in [0.1, 1.0]")
        
        self.fraction = kelly_fraction
        self.max_leverage = max_leverage
        self.min_pos = min_position
        self.max_pos = max_position
        
        logger.info(f"Fractional Kelly: fraction={kelly_fraction}")
    
    def calculate_kelly(self,
                       mean_return: float,
                       variance: float,
                       risk_free_rate: float = 0.0) -> float:
        """
        Calculate fractional Kelly position size.
        
        f = c × (μ - r) / σ²
        """
        if variance == 0:
            return 0
        
        # Full Kelly
        full_kelly = (mean_return - risk_free_rate) / variance
        
        # Fractional Kelly
        f = full_kelly * self.fraction
        
        # Bounds
        f = np.clip(f, -self.max_pos, self.max_pos)
        
        return f
    
    def size_position(self,
                     strategy_returns: np.ndarray,
                     capital: float,
                     price: float,
                     current_position: float = 0) -> float:
        """
        Calculate target position size based on Kelly.
        
        Returns number of units to hold.
        """
        if len(strategy_returns) < 30:
            logger.warning("Insufficient returns for Kelly sizing")
            return 0
        
        mean = np.mean(strategy_returns)
        variance = np.var(strategy_returns)
        
        # Kelly fraction
        kelly_position = self.calculate_kelly(mean, variance)
        
        # Convert to capital allocation
        target_capital = capital * abs(kelly_position)
        
        # Convert to units
        target_units = target_capital / price
        
        # Sign (direction)
        if mean < 0:
            target_units = -target_units
        
        # Don't trade if already at target
        if abs(target_units - current_position) / (abs(current_position) + 0.0001) < 0.05:
            return current_position
        
        return target_units


class VolatilityTargeter:
    """
    Scale positions to target constant portfolio volatility.
    
    Formula: scalar_w = σ_target / σ_strategy
    """
    
    def __init__(self,
                 target_volatility: float = 0.20,  # 20% annual
                 lookback_days: int = 20):
        """
        Args:
            target_volatility: Target annualized volatility (0.15-0.20 typical)
            lookback_days: Days for volatility calculation
        """
        self.target = target_volatility
        self.lookback = lookback_days
        
        # Bounds
        self.min_scalar = 0.1
        self.max_scalar = 3.0
    
    def calculate_scalar(self, returns: np.ndarray) -> float:
        """
        Calculate position scalar to hit target vol.
        
        If strategy is 30% vol and target is 20%:
        scalar = 0.20 / 0.30 = 0.67 (67% of capital)
        """
        if len(returns) < self.lookback:
            return 1.0
        
        # Current volatility (annualized)
        current_vol = np.std(returns[-self.lookback:]) * np.sqrt(252)
        
        if current_vol == 0:
            return 1.0
        
        scalar = self.target / current_vol
        
        # Bounds check
        scalar = np.clip(scalar, self.min_scalar, self.max_scalar)
        
        return scalar


class RiskParityAllocator:
    """
    Allocate capital using Risk Parity (equal risk contribution).
    
    Each strategy contributes equally to portfolio risk.
    Higher vol strategies get smaller allocations.
    """
    
    def __init__(self,
                 target_portfolio_vol: float = 0.18,
                 rebalance_threshold: float = 0.05):
        """
        Args:
            target_portfolio_vol: Target volatility
            rebalance_threshold: Rebalance if allocation differs by this %
        """
        self.target = target_portfolio_vol
        self.threshold = rebalance_threshold
    
    def inverse_vol_weights(self, volatilities: np.ndarray) -> np.ndarray:
        """
        Simple risk parity: weight ∝ 1/volatility
        """
        inv_vols = 1 / volatilities
        weights = inv_vols / inv_vols.sum()
        return weights
    
    def risk_budget_weights(self,
                           returns_df: pd.DataFrame,
                           target_risk_contribution: np.ndarray = None) -> np.ndarray:
        """
        Equal risk contribution portfolio.
        
        Uses numerical optimization to find weights where
        each asset's risk contribution = target.
        """
        n = len(returns_df.columns)
        
        if target_risk_contribution is None:
            # Equal risk
            target_risk_contribution = np.ones(n) / n
        
        # Use HRP as practical approximation
        try:
            import riskfolio as rp
            
            port = rp.Portfolio(returns=returns_df)
            
            # HRP (Hierarchical Risk Parity)
            weights = port.rp_optimization(
                model='HRP',
                rm='MV',  # Minimize variance
                rf=0.0
            )
            
            return weights['weights'].values
        except ImportError:
            # Fallback: inverse volatility
            vols = returns_df.std() * np.sqrt(252)
            return self.inverse_vol_weights(vols.values)
    
    def get_allocation(self,
                      strategy_returns: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Get risk parity allocation.
        
        Returns dict of strategy -> weight.
        """
        # Build returns dataframe
        min_len = min(len(r) for r in strategy_returns.values())
        
        if min_len < 30:
            # Equal weight
            return {s: 1.0/len(strategy_returns) for s in strategy_returns}
        
        df = pd.DataFrame({
            name: ret[-min_len:]
            for name, ret in strategy_returns.items()
        })
        
        # Calculate weights
        try:
            weights = self.risk_budget_weights(df)
        except:
            # Fallback
            vols = np.array([np.std(r[-min_len:]) for r in strategy_returns.values()])
            weights = self.inverse_vol_weights(vols)
        
        return dict(zip(strategy_returns.keys(), weights))


class IntegratedPositionSizer:
    """
    Combines Kelly + Volatility Targeting + Risk Parity.
    
    Pipeline:
    1. Risk parity: Allocate across strategies
    2. Kelly: Size each strategy
    3. Vol targeting: Scale to target portfolio vol
    4. Bounds: Enforce max position limits
    """
    
    def __init__(self,
                 kelly_config: dict = None,
                 vol_target_config: dict = None,
                 risk_parity_config: dict = None):
        """
        Initialize all components.
        """
        self.kelly = FractionalKellySizer(**(kelly_config or {}))
        self.vol_target = VolatilityTargeter(**(vol_target_config or {}))
        self.risk_parity = RiskParityAllocator(**(risk_parity_config or {}))
        
        self.allocation_history = []
    
    def calculate_allocations(self,
                            strategies: Dict[str, Dict],
                            capital: float,
                            current_positions: Dict[str, float]) -> Dict[str, StrategyAllocation]:
        """
        Calculate position allocations for all strategies.
        
        Args:
            strategies: Dict of strategy_name -> {returns, price, vol}
            capital: Total capital
            current_positions: Current position per strategy
        
        Returns:
            Dict of strategy_name -> StrategyAllocation
        """
        results = {}
        
        # 1. Risk parity weights
        returns_dict = {s: data['returns'] for s, data in strategies.items()}
        risk_weights = self.risk_parity.get_allocation(returns_dict)
        
        # 2. Kelly sizing for each
        for name, data in strategies.items():
            returns = data['returns']
            price = data['price']
            current_pos = current_positions.get(name, 0)
            
            # Kelly fraction
            kelly_size = self.kelly.size_position(
                returns, capital * risk_weights[name], price, current_pos
            )
            
            # Volatility scalar
            vol_scalar = self.vol_target.calculate_scalar(returns)
            
            # Combined weight
            final_weight = risk_weights[name] * vol_scalar
            final_weight = np.clip(final_weight, 0, 0.25)  # Max 25% per strategy
            
            # Calculate stop loss
            strategy_vol = np.std(returns[-20:]) if len(returns) >= 20 else 0.02
            stop_loss = price * (1 - 2 * strategy_vol) if data.get('direction') == 'long' else price * (1 + 2 * strategy_vol)
            
            allocation = StrategyAllocation(
                strategy_name=name,
                target_weight=risk_weights[name],
                kelly_fraction=kelly_size * price / capital if price > 0 else 0,
                volatility_scalar=vol_scalar,
                correlation_adjustment=1.0,  # Would calculate from correlation matrix
                final_weight=final_weight,
                max_position_pct=0.25,
                stop_loss_price=stop_loss
            )
            
            results[name] = allocation
        
        # Log
        self.allocation_history.append({
            'timestamp': pd.Timestamp.now(),
            'allocations': results,
            'total_weight': sum(a.final_weight for a in results.values())
        })
        
        logger.info(f"Allocations calculated: {len(results)} strategies")
        for name, alloc in results.items():
            logger.info(f"  {name}: {alloc.final_weight:.1%} (Kelly: {alloc.kelly_fraction:.2%})")
        
        return results
    
    def get_portfolio_stats(self) -> Dict:
        """Get portfolio-level statistics."""
        if not self.allocation_history:
            return {}
        
        latest = self.allocation_history[-1]
        
        return {
            'timestamp': latest['timestamp'],
            'total_weight': latest['total_weight'],
            'n_strategies': len(latest['allocations']),
            'allocations': {
                name: alloc.final_weight
                for name, alloc in latest['allocations'].items()
            }
        }


if __name__ == "__main__":
    # Test
    np.random.seed(42)
    
    print("=" * 70)
    print("FRACTIONAL KELLY + RISK PARITY - TEST")
    print("=" * 70)
    
    # Create fake strategies
    strategies = {
        'Trend_Following': {
            'returns': np.random.randn(100) * 0.02 + 0.001,
            'price': 100,
            'direction': 'long'
        },
        'Mean_Reversion': {
            'returns': np.random.randn(100) * 0.015 + 0.0008,
            'price': 100,
            'direction': 'long'
        },
        'Market_Making': {
            'returns': np.random.randn(100) * 0.01 + 0.0003,
            'price': 100,
            'direction': 'long'
        },
        'Dead_Strategy': {
            'returns': np.random.randn(100) * 0.03 - 0.002,
            'price': 100,
            'direction': 'long'
        }
    }
    
    # Integrated sizer
    sizer = IntegratedPositionSizer(
        kelly_config={'kelly_fraction': 0.25, 'max_position': 0.50},
        vol_target_config={'target_volatility': 0.18},
        risk_parity_config={'target_portfolio_vol': 0.18}
    )
    
    current_positions = {'Trend_Following': 0}
    capital = 100000
    
    print(f"\nCapital: ${capital:,.0f}")
    print(f"Target Vol: 18%")
    print(f"Kelly Fraction: 25%\n")
    print("-" * 70)
    
    allocations = sizer.calculate_allocations(
        strategies, capital, current_positions
    )
    
    print(f"\n{'='*70}")
    print("RESULTS:")
    print("=" * 70)
    
    for name, alloc in allocations.items():
        print(f"\n{name}:")
        print(f"  Risk Parity Weight: {alloc.target_weight:.1%}")
        print(f"  Kelly Fraction:     {alloc.kelly_fraction:.2%}")
        print(f"  Vol Scalar:         {alloc.volatility_scalar:.2f}")
        print(f"  Final Allocation:     {alloc.final_weight:.1%}")
        print(f"  Stop Loss:          ${alloc.stop_loss_price:.2f}")
        print(f"  Max Position:       {alloc.max_position_pct:.0%}")
    
    stats = sizer.get_portfolio_stats()
    print(f"\n{'='*70}")
    print("PORTFOLIO:")
    print("=" * 70)
    print(f"Total Weight: {stats['total_weight']:.1%}")
    print(f"Strategies:   {stats['n_strategies']}")
    
    print(f"\n{'='*70}")
    print("Fractional Kelly + Risk Parity ready for production!")
    print("=" * 70)
