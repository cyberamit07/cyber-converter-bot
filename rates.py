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
        """Fetch TON price from GetBlock API"""
        if not self.use_getblock:
            return 0
        
        try:
            headers = {
                "x-api-key": settings.getblock_api_key,
                "Content-Type": "application/json"
            }
            
            async with self.session.get(
                f"{settings.getblock_url}/v1/ton/price",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=settings.api_timeout)
            ) as response:
                if response.status != 200:
                    logger.warning(f"GetBlock API error: {response.status}")
                    return 0
                
                data = await response.json()
                price = data.get("price_usd", 0)
                if price and price > 0:
                    logger.info(f"✅ GetBlock TON price: ${price}")
                    return price
                return 0
        except Exception as e:
            logger.warning(f"GetBlock API exception: {e}")
            return 0
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)))
    )
    async def _fetch_coingecko(self) -> Dict[str, float]:
        """Fetch rates from CoinGecko"""
        try:
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
                return {
                    'ton': data.get('the-open-network', {}).get('usd', 0),
                    'usdt': data.get('tether', {}).get('usd', 0),
                    'usd': 1.0,
                }
        except Exception as e:
            logger.warning(f"CoinGecko API failed: {e}")
            return {'ton': 0, 'usdt': 1.0, 'usd': 1.0}
    
    async def _get_fiat_rates(self) -> Dict[str, float]:
        """Get fiat currency rates"""
        fallback = {'inr': 83.0, 'rub': 92.0, 'eur': 0.92}
        
        try:
            async with self.session.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    rates = data.get('rates', {})
                    return {
                        'inr': rates.get('INR', fallback['inr']),
                        'rub': rates.get('RUB', fallback['rub']),
                        'eur': rates.get('EUR', fallback['eur']),
                    }
                return fallback
        except:
            return fallback
    
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
            
            # Get TON price from GetBlock
            ton_price = await self._fetch_ton_getblock()
            
            # Get crypto rates from CoinGecko
            crypto_rates = await self._fetch_coingecko()
            
            # Get fiat rates
            fiat_rates = await self._get_fiat_rates()
            
            # Build rates dict
            rates = {
                'ton': ton_price if ton_price > 0 else crypto_rates.get('ton', 2.5),
                'usdt': crypto_rates.get('usdt', 1.0),
                'usd': 1.0,
                'inr': fiat_rates.get('inr', 83.0),
                'rub': fiat_rates.get('rub', 92.0),
                'eur': fiat_rates.get('eur', 0.92),
                'star': await self._get_star_rate(),
            }
            
            # Cache the rates
            await cache.set(self.cache_key, rates, ttl=settings.cache_ttl)
            self.last_fetch_time = datetime.now()
            
            logger.info(f"✅ Rates updated: TON=${rates['ton']:.4f}")
            return rates
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch rates: {e}")
            # Return cached or fallback
            cached = await cache.get(self.cache_key)
            if cached:
                return cached
            
            fallback = {
                'ton': 2.5, 'usdt': 1.0, 'usd': 1.0,
                'inr': 83.0, 'rub': 92.0, 'eur': 0.92, 'star': 0.01,
            }
            await cache.set(self.cache_key, fallback, ttl=30)
            return fallback
    
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
