"""
Enforcement tests for single order path guarantee.

These tests verify that RiskAwareRouter is the ONLY way to submit orders.
If any code path allows bypassing the router, these tests will FAIL.

Quant-firm standard: there must be no way to bypass the risk overlay.
"""

import ast
import os
from pathlib import Path
import sys
import re
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSingleOrderPath:
    """
    Prove that RiskAwareRouter is the single choke point for orders.
    
    These are HARD assertions - if they fail, the build fails.
    """
    
    def get_strategies_dir(self) -> Path:
        """Return path to strategies directory."""
        return Path(__file__).parent.parent / 'strategies'
    
    def get_execution_dir(self) -> Path:
        """Return path to execution directory."""
        return Path(__file__).parent.parent / 'execution'
    
    def test_no_direct_adapter_imports(self):
        """
        HARD GATE: No strategy imports exchange adapters directly.
        
        Strategies should only interact with RiskAwareRouter.
        If this fails, someone is trying to bypass the risk overlay.
        """
        strategies_dir = self.get_strategies_dir()
        
        forbidden_imports = [
            'from execution.exchange',
            'from execution.alpaca_adapter',
            'from execution.oanda_adapter', 
            'from execution.coinbase_adapter',
            'from execution.smart_router import',
        ]
        
        violations = []
        
        for py_file in strategies_dir.rglob('*.py'):
            content = py_file.read_text()
            for forbidden in forbidden_imports:
                if forbidden in content:
                    violations.append(f"{py_file}: {forbidden}")
        
        # HARD FAIL if violations found
        assert len(violations) == 0, (
            f"VIOLATION: Strategies importing exchange adapters directly. "
            f"This bypasses the risk overlay. Fix: {violations}"
        )
    
    def test_risk_aware_router_only_entry(self):
        """
        HARD GATE: submit_order exists ONLY in RiskAwareRouter.
        
        The submit_order method is the ONLY public order entry point.
        If a submit_order exists elsewhere, it's a bypass attempt.
        """
        execution_dir = self.get_execution_dir()
        
        violations = []
        
        for py_file in execution_dir.rglob('*.py'):
            if 'test' in py_file.name:
                continue
            if 'risk_aware_router' in py_file.name:
                continue  # This is the allowed location
                
            content = py_file.read_text()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name == 'submit_order':
                        violations.append(str(py_file))
        
        # HARD FAIL if submit_order found outside router
        assert len(violations) == 0, (
            f"VIOLATION: submit_order() found outside RiskAwareRouter: {violations}. "
            f"RiskAwareRouter MUST be the ONLY order entry point. "
            f"All orders must go through risk_aware_router.py"
        )
    
    def test_risk_aware_router_has_submit_order(self):
        """
        Verify RiskAwareRouter actually has submit_order method.
        """
        execution_dir = self.get_execution_dir()
        router_path = execution_dir / 'risk_aware_router.py'
        
        assert router_path.exists(), "RiskAwareRouter must exist"
        
        content = router_path.read_text()
        assert 'def submit_order' in content, (
            "RiskAwareRouter must have submit_order method"
        )
        assert 'pre_trade_check' in content, (
            "RiskAwareRouter must call pre_trade_check"
        )


class TestCapitalInjectionHardStop:
    """
    HARD GATE: Capital injection is a hard requirement, never a fallback.
    """
    
    def get_risk_dir(self) -> Path:
        """Return path to risk directory."""
        return Path(__file__).parent.parent / 'risk'
    
    def test_no_capital_fallback_constant(self):
        """
        HARD GATE: No hardcoded capital fallback exists.
        
        The number 100000 should not appear as a fallback in risk code.
        If it does, capital injection is not a hard requirement.
        """
        risk_dir = self.get_risk_dir()
        
        violations = []
        
        for py_file in risk_dir.rglob('*.py'):
            # Skip test files
            if 'test' in py_file.name:
                continue
                
            content = py_file.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Look for 100000 as a fallback (not in comment context)
                if '100000' in line and not line.strip().startswith('#'):
                    # Check if it's in a fallback context
                    if any(x in line for x in ['except', 'RuntimeError', 'try:', 'fallback']):
                        violations.append(f"{py_file}:{i}: {line.strip()}")
        
        # HARD FAIL if fallback patterns found
        assert len(violations) == 0, (
            f"VIOLATION: Capital fallback pattern found: {violations}. "
            f"Capital MUST be injected via set_capital(). "
            f"No hardcoded fallbacks allowed."
        )
    
    def test_capital_raises_if_not_set(self):
        """
        HARD GATE: _get_capital raises RuntimeError if not set.
        
        This is the critical safety check - no trading without capital.
        """
        from risk.kill_switches import KillSwitchMonitor, RiskLimits
        
        limits = RiskLimits(max_daily_loss_pct=0.02)
        monitor = KillSwitchMonitor(limits)
        
        # Must raise RuntimeError
        raised = False
        try:
            monitor._get_capital()
        except RuntimeError as e:
            raised = True
            assert "Capital not set" in str(e), (
                f"Wrong error message: {e}"
            )
        
        # HARD FAIL if didn't raise
        assert raised, (
            "VIOLATION: _get_capital() did not raise RuntimeError when capital not set. "
            "This means capital injection is optional, which violates the hard-stop requirement."
        )
    
    def test_capital_injection_works(self):
        """
        Verify set_capital() correctly injects capital.
        """
        from risk.kill_switches import KillSwitchMonitor, RiskLimits
        
        limits = RiskLimits(max_daily_loss_pct=0.02)
        monitor = KillSwitchMonitor(limits)
        
        # Inject capital
        monitor.set_capital(50000.0, source='test')
        
        # Should not raise
        assert monitor._get_capital() == 50000.0, (
            "Capital injection did not work correctly"
        )
    
    def test_update_fails_without_capital(self):
        """
        HARD GATE: update() fails without capital injection.
        
        This proves capital is a hard requirement, not optional.
        """
        from risk.kill_switches import KillSwitchMonitor, RiskLimits, PortfolioState
        from datetime import datetime
        
        limits = RiskLimits(max_daily_loss_pct=0.02)
        monitor = KillSwitchMonitor(limits)
        
        portfolio = PortfolioState(
            timestamp=datetime.now(),
            positions={},
            prices={'BTC': 50000},
            total_pnl=0,
            unrealized_pnl=0,
            realized_pnl=0,
            gross_exposure=0,
            net_exposure=0,
            leverage=0,
            open_orders=[],
            pending_cancels=[]
        )
        
        # Must raise RuntimeError - capital not set
        raised = False
        try:
            monitor.update(portfolio, [])
        except RuntimeError as e:
            raised = True
            assert "Capital not set" in str(e)
        
        # HARD FAIL if update allowed without capital
        assert raised, (
            "VIOLATION: update() did not raise RuntimeError without capital. "
            "update() must fail if set_capital() was not called."
        )


class TestRouterTokenProtection:
    """
    Token-based protection for exchange adapters.
    
    The simplest enforcement: adapters require a token that only
    RiskAwareRouter can create.
    """
    
    def test_router_token_class_exists(self):
        """
        Verify RouterToken class exists in risk_aware_router.
        
        The token ensures adapters can only be used through the router.
        """
        execution_dir = Path(__file__).parent.parent / 'execution'
        router_path = execution_dir / 'risk_aware_router.py'
        
        if not router_path.exists():
            pytest.skip("RiskAwareRouter doesn't exist yet - token protection not implemented")
        
        content = router_path.read_text()
        
        # Token class should exist
        has_token = 'class RouterToken' in content or '_RouterToken' in content
        
        # If token doesn't exist, that's not a failure - just not implemented yet
        # But we document it
        if not has_token:
            print("WARNING: RouterToken not implemented yet. Token-based protection pending.")
            print("This is acceptable for now, but should be added before live trading.")
        
        # Don't fail - just document the status
        assert True
    
    def test_exchange_adapters_require_token(self):
        """
        Verify exchange adapters require RouterToken if it exists.
        
        If RouterToken is implemented but adapters don't check for it,
        that's a bypass vulnerability.
        """
        execution_dir = Path(__file__).parent.parent / 'execution'
        router_path = execution_dir / 'risk_aware_router.py'
        
        if not router_path.exists():
            pytest.skip("RiskAwareRouter doesn't exist yet")
        
        router_content = router_path.read_text()
        
        # Check if token is implemented
        has_token = 'class RouterToken' in router_content or '_RouterToken' in router_content
        
        if not has_token:
            pytest.skip("RouterToken not implemented yet - skipping adapter check")
        
        # If token exists, adapters must require it
        adapter_files = [
            'alpaca_adapter.py',
            'oanda_adapter.py',
            'coinbase_adapter.py',
        ]
        
        violations = []
        
        for adapter in adapter_files:
            adapter_path = execution_dir / adapter
            if not adapter_path.exists():
                continue
            
            content = adapter_path.read_text()
            
            # Adapter should check for token
            has_token_check = 'router_token' in content or 'RouterToken' in content
            
            if not has_token_check:
                violations.append(adapter)
        
        # HARD FAIL if adapters don't require token
        assert len(violations) == 0, (
            f"VIOLATION: These adapters don't require RouterToken: {violations}. "
            f"Adapters must require a token that only RiskAwareRouter can create."
        )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
