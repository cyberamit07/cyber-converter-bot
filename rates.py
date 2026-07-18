import logging
import asyncio
import aiohttp
from typing import Dict, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from config import settings
from cache import cache

logger = logging.getLogger(__name__)

class RateFetcher:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.last_fetch_time = None
        self.cache_key = "exchange_rates"
        self.use_getblock = bool(settings.getblock_api_key)
        
        if self.use_getblock:
            logger.info("✅ GetBlock API enabled for TON price")
        else:
            logger.warning("⚠️ GetBlock API disabled - using CoinGecko fallback")
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)))
    )
    async def _fetch_ton_getblock(self) -> float:
        """Fetch TON price from GetBlock API - FASTEST"""
        if not self.use_getblock:
            return 0
        
        headers = {
            "x-api-key": settings.getblock_api_key,
            "Content-Type": "application/json"
        }
        
        # GetBlock TON price endpoint
        async with self.session.get(
            f"{settings.getblock_url}/v1/ton/price",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=settings.api_timeout)
        ) as response:
            if response.status != 200:
                logger.warning(f"GetBlock API error: {response.status}")
                return 0
            
            data = await response.json()
            # Parse GetBlock response
            price = data.get("price_usd", 0)
            if price and price > 0:
                logger.info(f"✅ GetBlock TON price: ${price}")
                return price
            return 0
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)))
    )
    async def _fetch_coingecko(self) -> Dict[str, float]:
        """Fetch rates from CoinGecko (fallback)"""
        params = {
            "ids": "the-open-network,tether",
            "vs_currencies": "usd"
        }
        
        async with self.session.get(
            settings.coingecko_api,
            params=params,
            timeout=aiohttp.ClientTimeout(total=settings.api_timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"CoinGecko API error: {response.status}")
            
            data = await response.json()
            rates = {
                'ton': data.get('the-open-network', {}).get('usd', 0),
                'usdt': data.get('tether', {}).get('usd', 0),
                'usd': 1.0,
            }
            
            # Get fiat rates
            try:
                rates['inr'] = await self._get_fiat_rate("INR")
                rates['rub'] = await self._get_fiat_rate("RUB")
                rates['eur'] = await self._get_fiat_rate("EUR")
            except Exception as e:
                logger.warning(f"Failed to fetch fiat rates: {e}")
                rates['inr'] = 83.0
                rates['rub'] = 92.0
                rates['eur'] = 0.92
            
            return rates
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)))
    )
    async def _get_fiat_rate(self, currency: str) -> float:
        """Get fiat currency rate"""
        fallback_rates = {"INR": 83.0, "RUB": 92.0, "EUR": 0.92}
        
        try:
            async with self.session.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('rates', {}).get(currency, fallback_rates.get(currency, 0))
                return fallback_rates.get(currency, 0)
        except:
            return fallback_rates.get(currency, 0)
    
    async def _get_star_rate(self) -> float:
        """Telegram Stars rate (1 Star = $0.01 USD)"""
        return 0.01
    
    async def get_rates(self, force_refresh: bool = False) -> Optional[Dict[str, float]]:
        """Get exchange rates from cache or fetch new"""
        if not force_refresh:
            cached = await cache.get(self.cache_key)
            if cached:
                logger.info("📦 Using cached rates")
                return cached
        
        try:
            logger.info("🔄 Fetching fresh exchange rates...")
            
            # Get TON price from GetBlock (primary)
            ton_price = await self._fetch_ton_getblock()
            
            # Get other rates from CoinGecko
            try:
                rates = await self._fetch_coingecko()
            except Exception as e:
                logger.warning(f"CoinGecko API failed: {e}, using fallback")
                rates = {
                    'ton': 0,
                    'usdt': 1.0,
                    'usd': 1.0,
                    'inr': 83.0,
                    'rub': 92.0,
                    'eur': 0.92,
                }
            
            # Use GetBlock price if available, else fallback to CoinGecko
            if ton_price and ton_price > 0:
                rates['ton'] = ton_price
            elif rates.get('ton', 0) <= 0:
                rates['ton'] = 2.5  # Ultimate fallback
            
            # Get Star rate
            rates['star'] = await self._get_star_rate()
            
            # Cache the rates
            await cache.set(self.cache_key, rates, ttl=settings.cache_ttl)
            self.last_fetch_time = datetime.now()
            
            logger.info(f"✅ Rates updated: TON=${rates['ton']:.4f}, USDT=${rates['usdt']:.4f}")
            return rates
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch rates: {e}")
            # Return fallback rates from cache if available
            cached = await cache.get(self.cache_key)
            if cached:
                return cached
            
            # Ultimate fallback
            fallback_rates = {
                'ton': 2.5,
                'usdt': 1.0,
                'usd': 1.0,
                'inr': 83.0,
                'rub': 92.0,
                'eur': 0.92,
                'star': 0.01,
            }
            await cache.set(self.cache_key, fallback_rates, ttl=30)
            return fallback_rates
    
    async def get_conversion(self, currency: str, amount: float) -> Optional[Dict[str, float]]:
        """Get conversions for a currency"""
        rates = await self.get_rates()
        if not rates or currency not in rates:
            return None
        
        base_rate = rates[currency]
        conversions = {}
        
        for target, rate in rates.items():
            if target == currency:
                conversions[target] = amount
            else:
                conversions[target] = (amount / base_rate) * rate
        
        return conversions