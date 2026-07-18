"""
Caching module for exchange rates with TTL support.
Implements in-memory caching with automatic expiration.
"""

import time
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Cache:
    """
    Simple in-memory cache with TTL (Time-To-Live) support.
    Thread-safe and async-compatible.
    """
    
    def __init__(self, default_ttl: int = 30):
        """
        Initialize the cache with default TTL.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        logger.info(f"Cache initialized with TTL: {default_ttl}s")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value or None if expired/not found
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if entry has expired
            if entry["expires_at"] < datetime.now():
                logger.debug(f"Cache entry '{key}' expired")
                del self._cache[key]
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return entry["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self._default_ttl
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at
            }
            logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    async def cleanup(self) -> None:
        """Remove expired entries from cache."""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry["expires_at"] < now
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

# Global cache instance
cache = Cache(default_ttl=30)