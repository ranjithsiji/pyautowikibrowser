"""Port of AWB UnitTests/CacheTests.cs (ObjectCache).

Ported by hand. AWB's ArgumentNullException is ValueError and its ArgumentException for an
unsupported type is TypeError. Persistence is JSON instead of XML.
"""

import io
import time
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from awb_x.api.cache import ObjectCache


@pytest.fixture
def cache() -> Iterator[ObjectCache]:
    c = ObjectCache()
    yield c
    c.close()


def reload(cache: ObjectCache) -> ObjectCache:
    ms = io.StringIO()
    cache.save(ms)
    ms.seek(0)
    cache = ObjectCache()
    cache.load(ms)
    return cache


def test_get_and_set(cache: ObjectCache) -> None:
    assert cache.get(int, "foo") is None

    cache.set("foo", "bar")
    assert cache.get(str, "foo") == "bar"


def test_dont_mix_types(cache: ObjectCache) -> None:
    cache.set("foo", "bar")
    cache.add_type(int, timedelta(days=5))
    cache.set("foo", 42)

    assert cache.get(str, "foo") == "bar"
    assert cache.get(int, "foo") == 42


def test_expiry(cache: ObjectCache) -> None:
    expires_soon = timedelta(milliseconds=20)
    cache.add_type(int, expires_soon)

    # using default expiry time
    cache.set("foo", 42)
    assert cache.get(int, "foo") == 42
    time.sleep(0.06)
    assert cache.get(int, "foo") is None

    # using explicitly set time, absolute
    cache.set("foo", 42, datetime.now() + expires_soon)
    assert cache.get(int, "foo") == 42
    time.sleep(0.06)
    assert cache.get(int, "foo") is None

    # ...and relative
    cache.set("foo", 42, expires_soon)
    assert cache.get(int, "foo") == 42
    time.sleep(0.06)
    assert cache.get(int, "foo") is None

    # also after save/load
    cache.set("foo", 42, expires_soon)
    assert cache.get(int, "foo") == 42
    ms = io.StringIO()
    cache.save(ms)
    ms.seek(0)
    time.sleep(0.06)
    cache.load(ms)
    assert cache.get(int, "foo") is None


def test_persistence(cache: ObjectCache) -> None:
    cache.set("foo", "bar")
    cache = reload(cache)
    assert cache.get(str, "foo") == "bar"


def test_loading_erases_storage(cache: ObjectCache) -> None:
    cache.set("foo", "bar")

    ms = io.StringIO()
    cache.save(ms)
    ms.seek(0)

    cache.set("boz", "quux")

    cache.load(ms)
    assert cache.get(str, "boz") is None


def test_dont_store_unknown_types(cache: ObjectCache) -> None:
    with pytest.raises(TypeError):
        cache.set("foo", 3)


def test_disallow_null_keys(cache: ObjectCache) -> None:
    with pytest.raises(ValueError):
        cache.set(None, "foo")  # type: ignore[arg-type]


def test_disallow_empty_keys(cache: ObjectCache) -> None:
    with pytest.raises(ValueError):
        cache.set("", "foo")


def test_dont_store_null(cache: ObjectCache) -> None:
    with pytest.raises(ValueError):
        cache.set("foo", None)


def test_preset_caches_created(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AWB_X_HOME", str(tmp_path))
    monkeypatch.setattr(ObjectCache, "_global", None)
    assert ObjectCache.global_cache() is not None
