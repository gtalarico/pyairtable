"""
TTL-based caching for Airtable record fetches.

Caching is opt-in via :meth:`Api.enable_caching() <pyairtable.Api.enable_caching>`
and disabled by default. When enabled, calls to :meth:`~pyairtable.Table.all`,
:meth:`~pyairtable.Table.iterate`, and :meth:`~pyairtable.Table.first` will
return cached results if a fresh entry exists for the same query parameters.

Cached entries are automatically invalidated when records are created, updated,
or deleted through the same :class:`~pyairtable.Api` instance. Mutations made
by other clients or API tokens are *not* visible until the TTL expires.
"""

from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pyairtable.api.types import RecordDict

__all__ = ["CacheKey", "TableTTLConfig", "RecordCache"]


@dataclass(frozen=True)
class CacheKey:
    """
    Immutable, hashable representation of a record-list query.

    Two queries that would return the same logical result set produce
    equal ``CacheKey`` instances. Pagination internals (``offset``,
    ``page_size``) are excluded; ``max_records`` is included because
    it limits the total result set.
    """

    base_id: str
    table_id_or_name: str
    formula: str = ""
    cell_format: str = ""
    fields: Tuple[str, ...] = ()
    view: str = ""
    sort: Tuple[str, ...] = ()
    time_zone: str = ""
    user_locale: str = ""
    use_field_ids: bool = False
    max_records: Optional[int] = None

    @classmethod
    def from_query(
        cls,
        base_id: str,
        table_id_or_name: str,
        options: Dict[str, Any],
    ) -> "CacheKey":
        fields = options.get("fields", ())
        if isinstance(fields, (list, tuple)):
            fields = tuple(sorted(fields))

        sort = options.get("sort", ())
        if isinstance(sort, (list, tuple)):
            sort = tuple(sort)

        max_records = options.get("max_records")
        if max_records is not None:
            max_records = int(max_records)

        return cls(
            base_id=base_id,
            table_id_or_name=table_id_or_name,
            formula=str(options.get("formula", "") or ""),
            cell_format=str(options.get("cell_format", "") or ""),
            fields=fields,
            view=str(options.get("view", "") or ""),
            sort=sort,
            time_zone=str(options.get("time_zone", "") or ""),
            user_locale=str(options.get("user_locale", "") or ""),
            use_field_ids=bool(options.get("use_field_ids", False)),
            max_records=max_records,
        )


@dataclass
class _CacheEntry:
    """A cached record set with bookkeeping metadata."""

    records: List[RecordDict]
    stored_at: float
    hit_count: int = 0


@dataclass(frozen=True)
class TableTTLConfig:
    """
    Per-table TTL configuration for the record cache.

    Args:
        default_ttl_seconds: Fallback TTL applied to any table without an override.
        overrides: Mapping of table name/ID to TTL in seconds.
        max_entries: Maximum number of cache entries before the oldest is evicted.
    """

    default_ttl_seconds: int = 300
    overrides: Dict[str, int] = field(default_factory=dict)
    max_entries: int = 1024

    def ttl_for_table(self, table_name: str) -> int:
        return self.overrides.get(table_name, self.default_ttl_seconds)


class RecordCache:
    """
    Thread-safe, TTL-based cache for complete record-list results.

    Entries are keyed by :class:`CacheKey` and store the fully-assembled
    list of records (all pages merged). Expired entries are lazily evicted
    on read; a hard cap (``max_entries``) provides a safety net against
    unbounded growth.
    """

    def __init__(self, config: TableTTLConfig) -> None:
        self._store: Dict[CacheKey, _CacheEntry] = {}
        self._lock = threading.Lock()
        self._config = config

    def get(self, key: CacheKey) -> Optional[List[RecordDict]]:
        """Return a deep copy of cached records, or ``None`` on miss/expiry."""
        ttl = self._config.ttl_for_table(key.table_id_or_name)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() - entry.stored_at > ttl:
                del self._store[key]
                return None
            entry.hit_count += 1
            return copy.deepcopy(entry.records)

    def put(self, key: CacheKey, records: List[RecordDict]) -> None:
        """Store a deep copy of *records*, evicting the oldest entry if full."""
        entry = _CacheEntry(
            records=copy.deepcopy(records),
            stored_at=time.monotonic(),
        )
        with self._lock:
            self._store[key] = entry
            if len(self._store) > self._config.max_entries:
                oldest_key = min(
                    self._store, key=lambda k: self._store[k].stored_at
                )
                del self._store[oldest_key]

    def invalidate_table(self, base_id: str, table_id_or_name: str) -> None:
        """Remove every entry whose key matches the given base + table."""
        with self._lock:
            to_remove = [
                k
                for k in self._store
                if k.base_id == base_id
                and k.table_id_or_name == table_id_or_name
            ]
            for k in to_remove:
                del self._store[k]

    def invalidate_all(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> Dict[str, Any]:
        """Snapshot of cache contents for debugging."""
        with self._lock:
            now = time.monotonic()
            entries = []
            for key, entry in self._store.items():
                entries.append(
                    {
                        "base_id": key.base_id,
                        "table": key.table_id_or_name,
                        "formula": key.formula or "(all)",
                        "view": key.view or "(default)",
                        "age_seconds": round(now - entry.stored_at, 1),
                        "hit_count": entry.hit_count,
                        "record_count": len(entry.records),
                    }
                )
            return {"total_entries": len(entries), "entries": entries}
