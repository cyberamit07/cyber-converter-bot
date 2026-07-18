import time
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self, default_ttl: int = 30):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            entry = self._cache[key]
            if entry["expires_at"] < datetime.now():
                del self._cache[key]
                return None
            return entry["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if ttl is None:
            ttl = self._default_ttl
        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl)
            }
    
    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

cache = Cache(default_ttl=30)