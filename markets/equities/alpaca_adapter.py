# Alpaca Market Adapter
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AlpacaAdapter:
    """
    Alpaca Markets adapter for equity trading.
    Supports both paper and live trading.
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        router_token=None,
        paper: bool = True,
    ):
        self._require_router_token(router_token)
        self._router_token = router_token
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper = paper
        
        # Base URLs
        if paper:
            self.base_url = "https://paper-api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"AlpacaAdapter initialized: paper={paper}")

    @staticmethod
    def _require_router_token(router_token) -> None:
        from execution.risk_aware_router import _is_valid_router_token

        if not _is_valid_router_token(router_token):
            raise RuntimeError(
                "AlpacaAdapter requires a valid _RouterToken issued by RiskAwareRouter."
            )

    def _assert_router_token(self, router_token=None) -> None:
        token = self._router_token if router_token is None else router_token
        self._require_router_token(token)
        if token is not self._router_token:
            raise RuntimeError("RouterToken mismatch for AlpacaAdapter order path.")
    
    async def connect(self):
        """Establish connection"""
        self.session = aiohttp.ClientSession()
        
        # Test connection
        try:
            account = await self.get_account()
            logger.info(f"Alpaca connection successful: {account['status']}")
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close connection"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _request(self, method: str, endpoint: str, 
                      base: str = 'trading', params: dict = None, 
                      json_data: dict = None) -> dict:
        """Make API request"""
        if not self.session:
            raise RuntimeError("Not connected")
        
        url = f"{self.base_url if base == 'trading' else self.data_url}{endpoint}"
        headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret
        }
        
        async with self.session.request(method, url, headers=headers, 
                                       params=params, json=json_data) as response:
            data = await response.json()
            
            if response.status not in [200, 201]:
                logger.error(f"Alpaca API error: {data}")
                raise Exception(f"API error: {data}")
            
            return data
    
    async def get_account(self) -> dict:
        """Get account information"""
        return await self._request('GET', '/v2/account')
    
    async def get_positions(self) -> List[dict]:
        """Get open positions"""
        return await self._request('GET', '/v2/positions')
    
    async def get_bars(self, symbol: str, timeframe: str = '1Hour',
                      start: datetime = None, end: datetime = None,
                      limit: int = 100) -> List[dict]:
        """Get historical price bars"""
        params = {
            'symbols': symbol,
            'timeframe': timeframe,
            'limit': limit
        }
        
        if start:
            params['start'] = start.isoformat()
        if end:
            params['end'] = end.isoformat()
        
        response = await self._request('GET', '/v2/stocks/bars', 
                                      base='data', params=params)
        return response.get(symbol, [])
    
    async def get_latest_quote(self, symbol: str) -> dict:
        """Get latest quote"""
        response = await self._request('GET', f'/v2/stocks/{symbol}/quotes/latest',
                                      base='data')
        return response.get('quote', {})
    
    async def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = 'market',
        limit_price: float = None,
        stop_price: float = None,
        router_token=None,
    ) -> dict:
        """Place an order"""
        self._assert_router_token(router_token)

        order_data = {
            'symbol': symbol,
            'qty': str(qty),
            'side': side.lower(),
            'type': order_type.lower(),
            'time_in_force': 'day'
        }
        
        if limit_price:
            order_data['limit_price'] = str(limit_price)
        if stop_price:
            order_data['stop_price'] = str(stop_price)
        
        return await self._request('POST', '/v2/orders', json_data=order_data)
    
    async def get_orders(self, status: str = 'open') -> List[dict]:
        """Get orders"""
        params = {'status': status}
        return await self._request('GET', '/v2/orders', params=params)
    
    async def cancel_order(self, order_id: str) -> None:
        """Cancel an order"""
        await self._request('DELETE', f'/v2/orders/{order_id}')
