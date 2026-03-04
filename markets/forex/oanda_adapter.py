# OANDA Forex Adapter
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OandaAdapter:
    """
    OANDA adapter for forex trading.
    """
    
    def __init__(self, api_key: str, account_id: str, practice: bool = True):
        self.api_key = api_key
        self.account_id = account_id
        self.practice = practice
        
        # Base URL
        if practice:
            self.base_url = "https://api-fxpractice.oanda.com"
        else:
            self.base_url = "https://api-fxtrade.oanda.com"
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"OandaAdapter initialized: practice={practice}")
    
    async def connect(self):
        """Establish connection"""
        self.session = aiohttp.ClientSession()
        
        try:
            account = await self.get_account()
            logger.info(f"OANDA connection successful: {account['account']['balance']}")
        except Exception as e:
            logger.error(f"OANDA connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close connection"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _request(self, method: str, endpoint: str, 
                      params: dict = None, json_data: dict = None) -> dict:
        """Make API request"""
        if not self.session:
            raise RuntimeError("Not connected")
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        async with self.session.request(method, url, headers=headers,
                                       params=params, json=json_data) as response:
            data = await response.json()
            
            if response.status not in [200, 201]:
                logger.error(f"OANDA API error: {data}")
                raise Exception(f"API error: {data}")
            
            return data
    
    async def get_account(self) -> dict:
        """Get account information"""
        return await self._request('GET', f'/v3/accounts/{self.account_id}')
    
    async def get_instruments(self) -> List[dict]:
        """Get available instruments"""
        response = await self._request('GET', 
            f'/v3/accounts/{self.account_id}/instruments')
        return response.get('instruments', [])
    
    async def get_candles(self, instrument: str, granularity: str = 'H1',
                         count: int = 500) -> List[dict]:
        """Get historical candles"""
        params = {
            'granularity': granularity,
            'count': count,
            'price': 'MBA'  # mid, bid, ask
        }
        
        response = await self._request('GET',
            f'/v3/instruments/{instrument}/candles', params=params)
        return response.get('candles', [])
    
    async def get_pricing(self, instruments: List[str]) -> List[dict]:
        """Get current pricing"""
        params = {'instruments': ','.join(instruments)}
        response = await self._request('GET',
            f'/v3/accounts/{self.account_id}/pricing', params=params)
        return response.get('prices', [])
    
    async def place_order(self, instrument: str, units: float,
                         order_type: str = 'MARKET',
                         price: float = None,
                         stop_loss: float = None,
                         take_profit: float = None) -> dict:
        """Place an order"""
        order_data = {
            'order': {
                'type': order_type.upper(),
                'instrument': instrument,
                'units': str(units)
            }
        }
        
        if price:
            order_data['order']['price'] = str(price)
        if stop_loss:
            order_data['order']['stopLossOnFill'] = {
                'price': str(stop_loss)
            }
        if take_profit:
            order_data['order']['takeProfitOnFill'] = {
                'price': str(take_profit)
            }
        
        return await self._request('POST',
            f'/v3/accounts/{self.account_id}/orders', json_data=order_data)
    
    async def get_trades(self) -> List[dict]:
        """Get open trades"""
        response = await self._request('GET',
            f'/v3/accounts/{self.account_id}/openTrades')
        return response.get('trades', [])
    
    async def close_trade(self, trade_id: str, units: float = None) -> dict:
        """Close a trade"""
        data = {}
        if units:
            data['units'] = str(units)
        
        return await self._request('PUT',
            f'/v3/accounts/{self.account_id}/trades/{trade_id}/close',
            json_data=data)
