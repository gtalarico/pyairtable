from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from pyairtable.api.caching import CacheEntry, RequestCache, TableTTLConfig


FAKE_BASE_ID = "appFAKEBASE123"
FAKE_TABLE = "TestTable"

SAMPLE_RECORDS = [
    {"id": "rec1", "fields": {"Name": "Alpha"}},
    {"id": "rec2", "fields": {"Name": "Beta"}},
]


def _make_cache(
    default_ttl: int = 300, overrides: dict[str, int] | None = None
) -> RequestCache:
    config = TableTTLConfig(
        default_ttl_seconds=default_ttl,
        overrides=overrides or {},
    )
    return RequestCache(config)


class TestTableTTLConfig:
    def test_default_ttl(self) -> None:
        config = TableTTLConfig(default_ttl_seconds=300)
        assert config.ttl_for_table("Anything") == 300

    def test_override_ttl(self) -> None:
        config = TableTTLConfig(
            default_ttl_seconds=300,
            overrides={"Workstreams": 900},
        )
        assert config.ttl_for_table("Workstreams") == 900
        assert config.ttl_for_table("Initiatives") == 300

    def test_frozen_config(self) -> None:
        config = TableTTLConfig(default_ttl_seconds=300)
        with pytest.raises(AttributeError):
            config.default_ttl_seconds = 100  # type: ignore


class TestCacheEntry:
    def test_cache_entry_creation(self) -> None:
        entry = CacheEntry(records=SAMPLE_RECORDS, stored_at_seconds=time.monotonic())
        assert entry.records == SAMPLE_RECORDS
        assert entry.hit_count == 0

    def test_cache_entry_hit_count(self) -> None:
        entry = CacheEntry(records=SAMPLE_RECORDS, stored_at_seconds=time.monotonic())
        entry.hit_count += 1
        entry.hit_count += 1
        assert entry.hit_count == 2


class TestRequestCache:
    def test_put_and_get_entry(self) -> None:
        cache = _make_cache()
        key = (FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False)
        cache.put_entry(key, SAMPLE_RECORDS)

        result = cache.get_entry(key)
        assert result == SAMPLE_RECORDS

    def test_miss_returns_none(self) -> None:
        cache = _make_cache()
        result = cache.get_entry((FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False))
        assert result is None

    def test_ttl_expiry(self) -> None:
        cache = _make_cache(default_ttl=10)
        key = (FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False)

        with patch("pyairtable.api.caching.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            cache.put_entry(key, SAMPLE_RECORDS)

            mock_time.monotonic.return_value = 1005.0
            assert cache.get_entry(key) == SAMPLE_RECORDS

            mock_time.monotonic.return_value = 1011.0
            assert cache.get_entry(key) is None

    def test_per_table_ttl_override(self) -> None:
        cache = _make_cache(default_ttl=300, overrides={"ShortLived": 5})
        key_short = (FAKE_BASE_ID, "ShortLived", "", "", (), "", (), False)
        key_long = (FAKE_BASE_ID, "LongLived", "", "", (), "", (), False)

        with patch("pyairtable.api.caching.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            cache.put_entry(key_short, SAMPLE_RECORDS)
            cache.put_entry(key_long, SAMPLE_RECORDS)

            mock_time.monotonic.return_value = 1006.0
            assert cache.get_entry(key_short) is None
            assert cache.get_entry(key_long) == SAMPLE_RECORDS

    def test_invalidate_table_removes_all_formulas(self) -> None:
        cache = _make_cache()
        key_no_formula = (FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False)
        key_with_formula = (FAKE_BASE_ID, FAKE_TABLE, "{Quarter}='Q3'", "", (), "", (), False)
        other_table_key = (FAKE_BASE_ID, "OtherTable", "", "", (), "", (), False)

        cache.put_entry(key_no_formula, SAMPLE_RECORDS)
        cache.put_entry(key_with_formula, SAMPLE_RECORDS)
        cache.put_entry(other_table_key, SAMPLE_RECORDS)

        cache.invalidate_table(FAKE_BASE_ID, FAKE_TABLE)

        assert cache.get_entry(key_no_formula) is None
        assert cache.get_entry(key_with_formula) is None
        assert cache.get_entry(other_table_key) == SAMPLE_RECORDS

    def test_invalidate_all(self) -> None:
        cache = _make_cache()
        cache.put_entry((FAKE_BASE_ID, "A", "", "", (), "", (), False), SAMPLE_RECORDS)
        cache.put_entry((FAKE_BASE_ID, "B", "", "", (), "", (), False), SAMPLE_RECORDS)

        cache.invalidate_all()

        assert cache.get_entry((FAKE_BASE_ID, "A", "", "", (), "", (), False)) is None
        assert cache.get_entry((FAKE_BASE_ID, "B", "", "", (), "", (), False)) is None

    def test_stats(self) -> None:
        cache = _make_cache()
        cache.put_entry((FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False), SAMPLE_RECORDS)
        cache.get_entry((FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False))

        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["entries"][0]["table"] == FAKE_TABLE
        assert stats["entries"][0]["hit_count"] == 1
        assert stats["entries"][0]["record_count"] == 2

    def test_hit_count_increments(self) -> None:
        cache = _make_cache()
        key = (FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False)
        cache.put_entry(key, SAMPLE_RECORDS)

        cache.get_entry(key)
        cache.get_entry(key)
        cache.get_entry(key)

        stats = cache.stats()
        assert stats["entries"][0]["hit_count"] == 3

    def test_thread_safety(self) -> None:
        cache = _make_cache(default_ttl=1)
        key = (FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False)
        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(50):
                    cache.get_entry(key)
            except Exception as exc:
                errors.append(exc)

        def writer() -> None:
            try:
                for _ in range(50):
                    cache.put_entry(key, SAMPLE_RECORDS)
            except Exception as exc:
                errors.append(exc)

        cache.put_entry(key, SAMPLE_RECORDS)
        threads = [threading.Thread(target=reader) for _ in range(4)]
        threads += [threading.Thread(target=writer) for _ in range(2)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_different_cache_keys_separate(self) -> None:
        cache = _make_cache()
        key1 = (FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False)
        key2 = (FAKE_BASE_ID, FAKE_TABLE, "{Name}='Alpha'", "", (), "", (), False)
        key3 = (FAKE_BASE_ID, FAKE_TABLE, "", "", ("Field1", "Field2"), "", (), False)

        records1 = [{"id": "rec1", "fields": {"Name": "One"}}]
        records2 = [{"id": "rec2", "fields": {"Name": "Two"}}]
        records3 = [{"id": "rec3", "fields": {"Name": "Three"}}]

        cache.put_entry(key1, records1)
        cache.put_entry(key2, records2)
        cache.put_entry(key3, records3)

        assert cache.get_entry(key1) == records1
        assert cache.get_entry(key2) == records2
        assert cache.get_entry(key3) == records3

    def test_stats_with_multiple_entries(self) -> None:
        cache = _make_cache()
        cache.put_entry((FAKE_BASE_ID, "Table1", "", "", (), "", (), False), SAMPLE_RECORDS)
        cache.put_entry((FAKE_BASE_ID, "Table2", "", "", (), "", (), False), SAMPLE_RECORDS)
        cache.put_entry((FAKE_BASE_ID, "Table1", "{Name}='Alpha'", "", (), "", (), False), SAMPLE_RECORDS)

        cache.get_entry((FAKE_BASE_ID, "Table1", "", "", (), "", (), False))
        cache.get_entry((FAKE_BASE_ID, "Table2", "", "", (), "", (), False))

        stats = cache.stats()
        assert stats["total_entries"] == 3
        assert len(stats["entries"]) == 3

    def test_expired_entry_removed_on_get(self) -> None:
        cache = _make_cache(default_ttl=5)
        key = (FAKE_BASE_ID, FAKE_TABLE, "", "", (), "", (), False)

        with patch("pyairtable.api.caching.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            cache.put_entry(key, SAMPLE_RECORDS)
            stats_before = cache.stats()
            assert stats_before["total_entries"] == 1

            mock_time.monotonic.return_value = 1006.0
            result = cache.get_entry(key)
            assert result is None

            stats_after = cache.stats()
            assert stats_after["total_entries"] == 0
