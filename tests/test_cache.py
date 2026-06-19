import asyncio
import pytest
from app.services.cache import MemoryCacheBackend


@pytest.fixture
def cache():
    return MemoryCacheBackend(max_size=100, ttl=3600)


@pytest.mark.asyncio
async def test_cache_set_get(cache):
    await cache.set("key1", {"data": "value"})
    result = await cache.get("key1")
    assert result == {"data": "value"}


@pytest.mark.asyncio
async def test_cache_miss(cache):
    result = await cache.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_cache_delete(cache):
    await cache.set("key1", "value")
    await cache.delete("key1")
    result = await cache.get("key1")
    assert result is None


@pytest.mark.asyncio
async def test_cache_delete_nonexistent(cache):
    # 삭제할 키가 없어도 에러 없음
    await cache.delete("nonexistent")


@pytest.mark.asyncio
async def test_cache_large_entry_skipped(cache):
    large_value = "x" * (6 * 1024 * 1024)  # 6MB
    await cache.set("large", large_value)
    result = await cache.get("large")
    assert result is None
