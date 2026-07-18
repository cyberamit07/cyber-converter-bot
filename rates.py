"""
Exchange rate fetching module with fallback support.
Handles API requests with retry logic and timeout management.
"""

import logging
import asyncio
import aiohttp
from typing import Dict, Optional, Any
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from config import settings
from cache import cache

logger = logging.getLogger(__name__)

class RateFetcher:
    """
    Fetches exchange rates from multiple APIs with fallback support.
    """
    
    def __init__(self, session: aiohttp.ClientSession):
        """
        Initialize rate fetcher with HTTP session.
        
        Args:
            session: aiohttp ClientSession instance
        """
        self.session = session
        self.last_fetch_time = None
        self.rate_cache_key = "exchange_rates"
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)))
    )
    async def _fetch_coingecko(self) -> Dict[str, float]:
        """
        Fetch rates from CoinGecko API.
        
        Returns:
            Dictionary of currency rates
        """
        params = {
            "ids": "the-open-network,tether,usd-coin",
            "vs_currencies": "usd,inr,rub,eur"
        }
        
        async with self.session.get(
            settings.coingecko_api,
            params=params,
            timeout=aiohttp.ClientTimeout(total=settings.api_timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"CoinGecko API returned status {response.status}")
            
            data = await response.json()
            
            # Extract rates
            rates = {
                'ton': data.get('the-open-network', {}).get('usd', 0),
                'usdt': data.get('tether', {}).get('usd', 0),
                'usd': 1.0,
            }
            
            # Add INR, RUB, EUR rates
            rates['inr'] = data.get('usd-coin', {}).get('inr', 0) or await self._get_inr_rate()
            rates['rub'] = data.get('usd-coin', {}).get('rub', 0) or await self._get_rub_rate()
            rates['eur'] = data.get('usd-coin', {}).get('eur', 0) or await self._get_eur_rate()
            
            return rates
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)))
    )
    async def _fetch_exchange_rate_api(self) -> Dict[str, float]:
        """
        Fetch rates from ExchangeRate API.
        
        Returns:
            Dictionary of currency rates
        """
        async with self.session.get(
            settings.exchange_rate_api,
            timeout=aiohttp.ClientTimeout(total=settings.api_timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"ExchangeRate API returned status {response.status}")
            
            data = await response.json()
            rates = data.get('rates', {})
            
            return {
                'inr': rates.get('INR', 0),
                'rub': rates.get('RUB', 0),
                'eur': rates.get('EUR', 0),
            }
    
    async def _get_inr_rate(self) -> float:
        """Get INR rate from ExchangeRate API."""
        try:
            rates = await self._fetch_exchange_rate_api()
            return rates.get('inr', 0)
        except Exception as e:
            logger.error(f"Failed to fetch INR rate: {e}")
            return 82.5  # Fallback approximate rate
    
    async def _get_rub_rate(self) -> float:
        """Get RUB rate from ExchangeRate API."""
        try:
            rates = await self._fetch_exchange_rate_api()
            return rates.get('rub', 0)
        except Exception as e:
            logger.error(f"Failed to fetch RUB rate: {e}")
            return 92.0  # Fallback approximate rate
    
    async def _get_eur_rate(self) -> float:
        """Get EUR rate from ExchangeRate API."""
        try:
            rates = await self._fetch_exchange_rate_api()
            return rates.get('eur', 0)
        except Exception as e:
            logger.error(f"Failed to fetch EUR rate: {e}")
            return 0.92  # Fallback approximate rate
    
    async def _get_star_rate(self) -> float:
        """
        Get Telegram Stars rate.
        Stars are typically valued at around $0.01 USD each.
        """
        return 0.01  # 1 Star = $0.01 USD
    
    async def get_rates(self, force_refresh: bool = False) -> Optional[Dict[str, float]]:
        """
        Get exchange rates from cache or fetch new ones.
        
        Args:
            force_refresh: Force refresh cache
            
        Returns:
            Dictionary of exchange rates or None if failed
        """
        # Check cache first
        if not force_refresh:
            cached_rates = await cache.get(self.rate_cache_key)
            if cached_rates:
                logger.info("Using cached exchange rates")
                return cached_rates
        
        try:
            logger.info("Fetching fresh exchange rates...")
            
            # Try CoinGecko first
            try:
                rates = await self._fetch_coingecko()
            except Exception as e:
                logger.warning(f"CoinGecko API failed: {e}")
                # Fallback to basic rates
                rates = {
                    'ton': 2.5,  # Fallback approximate
                    'usdt': 1.0,
                    'usd': 1.0,
                    'inr': 82.5,
                    'rub': 92.0,
                    'eur': 0.92,
                }
            
            # Get Star rate
            rates['star'] = await self._get_star_rate()
            
            # Cache the rates
            await cache.set(self.rate_cache_key, rates, ttl=settings.cache_ttl)
            self.last_fetch_time = datetime.now()
            
            logger.info(f"Exchange rates updated: {rates}")
            return rates
            
        except Exception as e:
            logger.error(f"Failed to fetch exchange rates: {e}")
            return None
    
    async def get_conversion(self, currency: str, amount: float) -> Optional[Dict[str, float]]:
        """
        Get conversion rates for a specific currency and amount.
        
        Args:
            currency: Source currency
            amount: Amount to convert
            
        Returns:
            Dictionary with all currency conversions
        """
        rates = await self.get_rates()
        if not rates:
            return None
        
        if currency not in rates:
            return None
        
        base_rate = rates[currency]
        conversions = {}
        
        for target_currency, target_rate in rates.items():
            if target_currency == currency:
                conversions[target_currency] = amount
            else:
                conversions[target_currency] = (amount / base_rate) * target_rate
        
        return conversions