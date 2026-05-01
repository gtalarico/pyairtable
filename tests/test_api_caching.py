from __future__ import annotations

import threading
from unittest.mock import patch

import pytest
from requests_mock import Mocker

from pyairtable import Api, Table, TableTTLConfig
from pyairtable.api.caching import CacheKey, RecordCache

FAKE_BASE_ID = "appFAKEBASE123"
FAKE_TABLE = "TestTable"

SAMPLE_RECORDS = [
    {
        "id": "rec1",
        "createdTime": "2024-01-01T00:00:00.000Z",
        "fields": {"Name": "Alpha"},
    },
    {
        "id": "rec2",
        "createdTime": "2024-01-01T00:00:00.000Z",
        "fields": {"Name": "Beta"},
    },
]


def _make_cache(
    default_ttl: int = 300,
    overrides: dict[str, int] | None = None,
    max_entries: int = 1024,
) -> RecordCache:
    config = TableTTLConfig(
        default_ttl_seconds=default_ttl,
        overrides=overrides or {},
        max_entries=max_entries,
    )
    return RecordCache(config)


# ---------------------------------------------------------------------------
# CacheKey
# ---------------------------------------------------------------------------


class TestCacheKey:
    def test_from_query_defaults(self) -> None:
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        assert key.base_id == FAKE_BASE_ID
        assert key.table_id_or_name == FAKE_TABLE
        assert key.options == ()

    def test_from_query_with_options(self) -> None:
        key = CacheKey.from_query(
            FAKE_BASE_ID,
            FAKE_TABLE,
            {
                "formula": "{Name}='Alpha'",
                "view": "Grid view",
                "fields": ["B", "A"],
                "sort": ["Name", "-Age"],
                "use_field_ids": True,
            },
        )
        assert key.option("formula") == "{Name}='Alpha'"
        assert key.option("view") == "Grid view"
        assert key.option("fields") == ("A", "B")
        assert key.option("sort") == ("Name", "-Age")
        assert key.option("use_field_ids") is True

    def test_fields_sorted_for_equality(self) -> None:
        k1 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"fields": ["B", "A"]})
        k2 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"fields": ["A", "B"]})
        assert k1 == k2

    def test_sort_order_preserved(self) -> None:
        k1 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"sort": ["Name", "-Age"]})
        k2 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"sort": ["-Age", "Name"]})
        assert k1 != k2

    def test_page_size_ignored(self) -> None:
        """page_size changes pagination, but not Table.all() results."""
        base = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        with_pagination = CacheKey.from_query(
            FAKE_BASE_ID,
            FAKE_TABLE,
            {"page_size": 100},
        )
        assert base == with_pagination

    def test_offset_included_in_key(self) -> None:
        """offset changes the returned result set, so it's part of the key."""
        k1 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        k2 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"offset": "itr123"})
        assert k1 != k2

    def test_max_records_included_in_key(self) -> None:
        """max_records limits the result set, so it's part of the key."""
        k1 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        k2 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"max_records": 50})
        assert k1 != k2

    def test_count_comments_included_in_key(self) -> None:
        """count_comments changes response metadata, so it's part of the key."""
        k1 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        k2 = CacheKey.from_query(
            FAKE_BASE_ID,
            FAKE_TABLE,
            {"count_comments": True},
        )
        assert k1 != k2

    def test_hashable(self) -> None:
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        d = {key: "value"}
        assert d[key] == "value"

    def test_none_values_treated_as_empty(self) -> None:
        k1 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"formula": None})
        k2 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        assert k1 == k2

    def test_false_values_treated_as_empty(self) -> None:
        k1 = CacheKey.from_query(
            FAKE_BASE_ID,
            FAKE_TABLE,
            {"count_comments": False},
        )
        k2 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        assert k1 == k2

    def test_freezes_nested_option_values(self) -> None:
        k1 = CacheKey.from_query(
            FAKE_BASE_ID,
            FAKE_TABLE,
            {"future": {"b": [2, 1], "a": {"x": "y"}}},
        )
        k2 = CacheKey.from_query(
            FAKE_BASE_ID,
            FAKE_TABLE,
            {"future": {"a": {"x": "y"}, "b": [2, 1]}},
        )
        assert k1 == k2

    def test_freezes_sets(self) -> None:
        k1 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"future": {2, 1}})
        k2 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"future": {1, 2}})
        assert k1 == k2

    def test_freezes_unhashable_objects(self) -> None:
        class Unhashable:
            __hash__ = None  # type: ignore

        key = CacheKey.from_query(
            FAKE_BASE_ID,
            FAKE_TABLE,
            {"future": Unhashable()},
        )
        assert "Unhashable" in key.option("future")

    def test_field_name_string_is_not_split(self) -> None:
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"fields": "Name"})
        assert key.option("fields") == "Name"

    def test_unusual_fields_value_falls_back_to_freeze(self) -> None:
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"fields": 123})
        assert key.option("fields") == 123


# ---------------------------------------------------------------------------
# TableTTLConfig
# ---------------------------------------------------------------------------


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

    def test_frozen(self) -> None:
        config = TableTTLConfig(default_ttl_seconds=300)
        with pytest.raises(AttributeError):
            config.default_ttl_seconds = 100  # type: ignore


# ---------------------------------------------------------------------------
# RecordCache unit tests
# ---------------------------------------------------------------------------


class TestRecordCache:
    def test_put_and_get(self) -> None:
        cache = _make_cache()
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        cache.put(key, SAMPLE_RECORDS)
        assert cache.get(key) == SAMPLE_RECORDS

    def test_miss_returns_none(self) -> None:
        cache = _make_cache()
        assert cache.get(CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})) is None

    def test_ttl_expiry(self) -> None:
        cache = _make_cache(default_ttl=10)
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})

        with patch("pyairtable.api.caching.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            cache.put(key, SAMPLE_RECORDS)

            mock_time.monotonic.return_value = 1005.0
            assert cache.get(key) == SAMPLE_RECORDS

            mock_time.monotonic.return_value = 1011.0
            assert cache.get(key) is None

    def test_per_table_ttl_override(self) -> None:
        cache = _make_cache(default_ttl=300, overrides={"ShortLived": 5})
        key_short = CacheKey.from_query(FAKE_BASE_ID, "ShortLived", {})
        key_long = CacheKey.from_query(FAKE_BASE_ID, "LongLived", {})

        with patch("pyairtable.api.caching.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            cache.put(key_short, SAMPLE_RECORDS)
            cache.put(key_long, SAMPLE_RECORDS)

            mock_time.monotonic.return_value = 1006.0
            assert cache.get(key_short) is None
            assert cache.get(key_long) == SAMPLE_RECORDS

    def test_invalidate_table(self) -> None:
        cache = _make_cache()
        k1 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        k2 = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {"formula": "x"})
        k3 = CacheKey.from_query(FAKE_BASE_ID, "Other", {})

        cache.put(k1, SAMPLE_RECORDS)
        cache.put(k2, SAMPLE_RECORDS)
        cache.put(k3, SAMPLE_RECORDS)

        cache.invalidate_table(FAKE_BASE_ID, [FAKE_TABLE])

        assert cache.get(k1) is None
        assert cache.get(k2) is None
        assert cache.get(k3) == SAMPLE_RECORDS

    def test_invalidate_all(self) -> None:
        cache = _make_cache()
        cache.put(CacheKey.from_query(FAKE_BASE_ID, "A", {}), SAMPLE_RECORDS)
        cache.put(CacheKey.from_query(FAKE_BASE_ID, "B", {}), SAMPLE_RECORDS)
        cache.invalidate_all()
        assert cache.get(CacheKey.from_query(FAKE_BASE_ID, "A", {})) is None

    def test_deep_copy_isolation(self) -> None:
        """Mutating returned records must not corrupt the cache."""
        cache = _make_cache()
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        original = [{"id": "rec1", "createdTime": "t", "fields": {"Name": "A"}}]
        cache.put(key, original)

        original[0]["fields"]["Name"] = "MUTATED"

        result = cache.get(key)
        assert result is not None
        assert result[0]["fields"]["Name"] == "A"

        result[0]["fields"]["Name"] = "ALSO_MUTATED"
        result2 = cache.get(key)
        assert result2 is not None
        assert result2[0]["fields"]["Name"] == "A"

    def test_max_entries_eviction(self) -> None:
        cache = _make_cache(max_entries=2)
        k1 = CacheKey.from_query(FAKE_BASE_ID, "T1", {})
        k2 = CacheKey.from_query(FAKE_BASE_ID, "T2", {})
        k3 = CacheKey.from_query(FAKE_BASE_ID, "T3", {})

        with patch("pyairtable.api.caching.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            cache.put(k1, SAMPLE_RECORDS)
            mock_time.monotonic.return_value = 200.0
            cache.put(k2, SAMPLE_RECORDS)
            mock_time.monotonic.return_value = 300.0
            cache.put(k3, SAMPLE_RECORDS)

            assert cache.get(k1) is None
            assert cache.get(k2) == SAMPLE_RECORDS
            assert cache.get(k3) == SAMPLE_RECORDS

    def test_stats(self) -> None:
        cache = _make_cache()
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        cache.put(key, SAMPLE_RECORDS)
        cache.get(key)

        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["entries"][0]["table"] == FAKE_TABLE
        assert stats["entries"][0]["hit_count"] == 1
        assert stats["entries"][0]["record_count"] == 2

    def test_thread_safety(self) -> None:
        cache = _make_cache(default_ttl=60)
        key = CacheKey.from_query(FAKE_BASE_ID, FAKE_TABLE, {})
        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(50):
                    cache.get(key)
            except Exception as exc:
                errors.append(exc)

        def writer() -> None:
            try:
                for _ in range(50):
                    cache.put(key, SAMPLE_RECORDS)
            except Exception as exc:
                errors.append(exc)

        cache.put(key, SAMPLE_RECORDS)
        threads = [threading.Thread(target=reader) for _ in range(4)]
        threads += [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


# ---------------------------------------------------------------------------
# Integration: Api + Table with caching enabled
# ---------------------------------------------------------------------------


class TestCachingIntegration:
    """Test that caching works end-to-end through Table.all / first."""

    @pytest.fixture()
    def api(self) -> Api:
        return Api("FakeApiKey")

    @pytest.fixture()
    def table(self, api: Api) -> Table:
        api.enable_caching()
        return api.table("appTEST123", "MyTable")

    def _mock_list_records(
        self,
        requests_mock: Mocker,
        table: Table,
        pages: list[dict],
    ) -> None:
        """Register paginated responses for table.urls.records."""
        responses = [{"json": page, "status_code": 200} for page in pages]
        requests_mock.get(table.urls.records, responses)

    def test_all_caches_across_pages(self, table: Table, requests_mock: Mocker) -> None:
        """table.all() assembles all pages, and the second call is a cache hit."""
        page1_records = [
            {"id": "rec1", "createdTime": "t", "fields": {"X": 1}},
            {"id": "rec2", "createdTime": "t", "fields": {"X": 2}},
        ]
        page2_records = [
            {"id": "rec3", "createdTime": "t", "fields": {"X": 3}},
        ]
        self._mock_list_records(
            requests_mock,
            table,
            [
                {"records": page1_records, "offset": "off1"},
                {"records": page2_records},
            ],
        )

        first_call = table.all()
        assert len(first_call) == 3
        assert requests_mock.call_count == 2

        second_call = table.all()
        assert second_call == first_call
        assert requests_mock.call_count == 2

    def test_iterate_not_cached_and_preserves_pages(
        self, table: Table, requests_mock: Mocker
    ) -> None:
        page1_records = [{"id": "rec1", "createdTime": "t", "fields": {}}]
        page2_records = [{"id": "rec2", "createdTime": "t", "fields": {}}]
        pages = [
            {"records": page1_records, "offset": "off1"},
            {"records": page2_records},
            {"records": page1_records, "offset": "off1"},
            {"records": page2_records},
        ]
        self._mock_list_records(requests_mock, table, pages)

        pages1 = list(table.iterate())
        pages2 = list(table.iterate())
        assert pages1 == [page1_records, page2_records]
        assert pages2 == [page1_records, page2_records]
        assert requests_mock.call_count == 4

    def test_first_caches(self, table: Table, requests_mock: Mocker) -> None:
        records = [{"id": "rec1", "createdTime": "t", "fields": {"A": 1}}]
        requests_mock.get(
            table.urls.records,
            [
                {"json": {"records": records}, "status_code": 200},
                {"json": {"records": records}, "status_code": 200},
            ],
        )

        r1 = table.first()
        r2 = table.first()
        assert r1 == r2
        assert requests_mock.call_count == 1

    def test_different_formulas_cached_separately(
        self, table: Table, requests_mock: Mocker
    ) -> None:
        rec_a = [{"id": "rec1", "createdTime": "t", "fields": {"X": "A"}}]
        rec_b = [{"id": "rec2", "createdTime": "t", "fields": {"X": "B"}}]

        # Two different formulas, each served once.
        requests_mock.get(
            table.urls.records,
            [
                {"json": {"records": rec_a}, "status_code": 200},
                {"json": {"records": rec_b}, "status_code": 200},
            ],
        )

        result_a = table.all(formula="{X}='A'")
        result_b = table.all(formula="{X}='B'")
        assert result_a != result_b
        assert requests_mock.call_count == 2

        result_a2 = table.all(formula="{X}='A'")
        assert result_a2 == result_a
        assert requests_mock.call_count == 2

    def test_count_comments_cached_separately(
        self, table: Table, requests_mock: Mocker
    ) -> None:
        without_comments = [{"id": "rec1", "createdTime": "t", "fields": {"X": 1}}]
        with_comments = [
            {
                "id": "rec1",
                "createdTime": "t",
                "fields": {"X": 1},
                "commentCount": 2,
            }
        ]
        requests_mock.get(
            table.urls.records,
            [
                {"json": {"records": without_comments}, "status_code": 200},
                {"json": {"records": with_comments}, "status_code": 200},
            ],
        )

        assert table.all() == without_comments
        assert table.all(count_comments=True) == with_comments
        assert table.all() == without_comments
        assert table.all(count_comments=True) == with_comments
        assert requests_mock.call_count == 2

    def test_mutation_invalidates_cache(
        self, table: Table, requests_mock: Mocker
    ) -> None:
        records = [{"id": "rec1", "createdTime": "t", "fields": {"X": 1}}]
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        assert requests_mock.call_count == 1

        # Second all() is a cache hit — no network.
        table.all()
        assert requests_mock.call_count == 1

        # Mutation invalidates cache.
        requests_mock.post(
            table.urls.records,
            json={
                "id": "rec2",
                "createdTime": "t",
                "fields": {"X": 2},
            },
        )
        table.create({"X": 2})
        assert requests_mock.call_count == 2

        # Re-register GET response for the post-invalidation fetch.
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        assert requests_mock.call_count == 3

    def test_mutation_invalidates_cache_for_quoted_table_name(
        self, api: Api, requests_mock: Mocker
    ) -> None:
        api.enable_caching()
        table = api.table("appTEST123", "My Table")
        records = [{"id": "rec1", "createdTime": "t", "fields": {"X": 1}}]
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        table.all()
        assert requests_mock.call_count == 1

        requests_mock.post(
            table.urls.records,
            json={
                "id": "rec2",
                "createdTime": "t",
                "fields": {"X": 2},
            },
        )
        table.create({"X": 2})
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        assert requests_mock.call_count == 3

    def test_mutation_invalidates_cache_after_schema_load(
        self, table: Table, requests_mock: Mocker
    ) -> None:
        records = [{"id": "rec1", "createdTime": "t", "fields": {"X": 1}}]
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        table._schema = type("Schema", (), {"id": "tblSchema"})()  # type: ignore

        requests_mock.post(
            table.urls.records,
            json={
                "id": "rec2",
                "createdTime": "t",
                "fields": {"X": 2},
            },
        )
        table.create({"X": 2})
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        assert requests_mock.call_count == 3

    def test_delete_invalidates_cache(
        self, table: Table, requests_mock: Mocker
    ) -> None:
        records = [{"id": "rec1", "createdTime": "t", "fields": {"X": 1}}]
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        assert requests_mock.call_count == 1

        requests_mock.delete(
            table.urls.records + "/rec1",
            json={"id": "rec1", "deleted": True},
        )
        table.delete("rec1")
        assert requests_mock.call_count == 2

        self._mock_list_records(requests_mock, table, [{"records": []}])
        table.all()
        assert requests_mock.call_count == 3

    def test_upload_attachment_invalidates_cache(
        self, table: Table, requests_mock: Mocker
    ) -> None:
        records = [{"id": "rec1", "createdTime": "t", "fields": {"X": 1}}]
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        table.all()
        assert requests_mock.call_count == 1

        requests_mock.post(
            table.urls.upload_attachment("rec1", "Attachments"),
            json={
                "id": "rec1",
                "createdTime": "t",
                "fields": {"Attachments": []},
            },
        )
        table.upload_attachment(
            "rec1",
            "Attachments",
            "example.txt",
            content="hello",
        )
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        assert requests_mock.call_count == 3

    def test_caching_disabled_by_default(self, requests_mock: Mocker) -> None:
        api = Api("FakeApiKey")
        tbl = api.table("appTEST123", "MyTable")

        records = [{"id": "rec1", "createdTime": "t", "fields": {}}]
        requests_mock.get(
            tbl.urls.records,
            [
                {"json": {"records": records}, "status_code": 200},
                {"json": {"records": records}, "status_code": 200},
            ],
        )

        tbl.all()
        tbl.all()
        assert requests_mock.call_count == 2

    def test_disable_caching(self, table: Table, requests_mock: Mocker) -> None:
        records = [{"id": "rec1", "createdTime": "t", "fields": {}}]
        requests_mock.get(
            table.urls.records,
            [
                {"json": {"records": records}, "status_code": 200},
                {"json": {"records": records}, "status_code": 200},
            ],
        )

        table.all()
        assert requests_mock.call_count == 1

        table.api.disable_caching()

        table.all()
        assert requests_mock.call_count == 2

    def test_cache_stats(self, table: Table, requests_mock: Mocker) -> None:
        records = [{"id": "rec1", "createdTime": "t", "fields": {}}]
        self._mock_list_records(requests_mock, table, [{"records": records}])
        table.all()
        table.all()

        stats = table.api.cache_stats()
        assert stats is not None
        assert stats["total_entries"] == 1
        assert stats["entries"][0]["hit_count"] == 1
        assert stats["entries"][0]["record_count"] == 1

    def test_cache_stats_disabled(self) -> None:
        api = Api("FakeApiKey")
        assert api.cache_stats() is None
