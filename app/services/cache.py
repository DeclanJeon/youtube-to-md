from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from cachetools import TTLCache


class CacheBackend(ABC):
    """캐시 추상 인터페이스."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...


class MemoryCacheBackend(CacheBackend):
    """cachetools.TTLCache 기반 메모리 캐시 구현."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=max_size, ttl=ttl)
        self._max_entry_size = 5 * 1024 * 1024  # 5MB

    async def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        import sys
        size = sys.getsizeof(value)
        if size > self._max_entry_size:
            return  # 대용량 엔트리는 캐시 미저장
        self._cache[key] = value

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)
