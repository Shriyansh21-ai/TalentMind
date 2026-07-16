"""Module 4 tests — distributed cache layer.

In-memory provider (clock-driven TTL, hit/miss stats), namespaces, tenant
isolation, invalidation, get_or_set, and the Redis placeholder behaviour.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.runtime.cache import (
    CacheManager,
    MemoryCacheProvider,
    RedisCacheProvider,
)


def test_memory_ttl_expires_on_clock_advance():
    clock = FrozenClock()
    provider = MemoryCacheProvider(clock=clock)
    provider.set("k", "v", ttl_seconds=60)
    assert provider.get("k") == "v"
    clock.advance(seconds=61)
    assert provider.get("k") is None


def test_hit_miss_statistics():
    clock = FrozenClock()
    provider = MemoryCacheProvider(clock=clock)
    provider.set("k", 1)
    provider.get("k")  # hit
    provider.get("absent")  # miss
    stats = provider.stats
    assert stats["hits"] == 1 and stats["misses"] == 1
    assert provider.hit_rate == 0.5


def test_namespaces_do_not_collide():
    manager = CacheManager(clock=FrozenClock())
    manager.session_cache.set("x", "session")
    manager.config_cache.set("x", "config")
    assert manager.session_cache.get("x") == "session"
    assert manager.config_cache.get("x") == "config"


def test_tenant_cache_is_isolated():
    manager = CacheManager(clock=FrozenClock())
    manager.tenant_cache.set_for("t1", "k", "one")
    manager.tenant_cache.set_for("t2", "k", "two")
    assert manager.tenant_cache.get_for("t1", "k") == "one"
    assert manager.tenant_cache.get_for("t2", "k") == "two"


def test_get_or_set_computes_once():
    manager = CacheManager(clock=FrozenClock())
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return "value"

    ns = manager.namespace("demo")
    assert ns.get_or_set("k", factory) == "value"
    assert ns.get_or_set("k", factory) == "value"
    assert calls["n"] == 1  # computed only once


def test_invalidate_all_clears_provider():
    manager = CacheManager(clock=FrozenClock())
    manager.analytics_cache.set("k", 1)
    manager.invalidate_all()
    assert manager.analytics_cache.get("k") is None


def test_redis_provider_is_placeholder():
    provider = RedisCacheProvider()
    with pytest.raises(Exception):
        provider.get("k")
