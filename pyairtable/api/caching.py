"""
TTL-based caching for Airtable record fetches.

Caching is opt-in via :meth:`Api.enable_caching() <pyairtable.Api.enable_caching>`
and disabled by default. When enabled, calls to :meth:`~pyairtable.Table.all`
and :meth:`~pyairtable.Table.first` will return cached results if a fresh
entry exists for the same query parameters.

Cached entries are automatically invalidated when records are created, updated,
or deleted through the same :class:`~pyairtable.Api` instance. Mutations made
by other clients or API tokens are *not* visible until the TTL expires.
"""

from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Hashable, Iterable, List, Optional, Tuple

from pyairtable.api.types import RecordDict

__all__ = ["CacheKey", "TableTTLConfig", "RecordCache"]


@dataclass(frozen=True)
class CacheKey:
    """
    Immutable, hashable representation of a record-list query.

    Two queries that would return the same logical result set produce
    equal ``CacheKey`` instances. ``page_size`` is excluded because it
    only controls request pagination; options like ``offset``,
    ``max_records``, and ``count_comments`` are included because they
    change the result set or response shape.
    """

    base_id: str
    table_id_or_name: str
    options: Tuple[Tuple[str, Hashable], ...] = ()

    @classmethod
    def from_query(
        cls,
        base_id: str,
        table_id_or_name: str,
        options: Dict[str, Any],
    ) -> "CacheKey":
        cache_options = []
        for name, value in options.items():
            if name == "page_size":
                continue
            if value is None or value is False:
                continue
            if name == "fields":
                value = cls._freeze_unordered(value)
            elif name in ("count_comments", "use_field_ids"):
                value = bool(value)
            elif name == "max_records":
                value = int(value)
            else:
                value = cls._freeze(value)
            cache_options.append((name, value))
        return cls(
            base_id=base_id,
            table_id_or_name=table_id_or_name,
            options=tuple(sorted(cache_options)),
        )

    @staticmethod
    def _freeze(value: Any) -> Hashable:
        if isinstance(value, dict):
            return tuple(
                sorted(
                    (str(key), CacheKey._freeze(item)) for key, item in value.items()
                )
            )
        if isinstance(value, (list, tuple)):
            return tuple(CacheKey._freeze(item) for item in value)
        if isinstance(value, (set, frozenset)):
            return tuple(sorted(CacheKey._freeze(item) for item in value))
        try:
            hash(value)
        except TypeError:
            return repr(value)
        return value

    @staticmethod
    def _freeze_unordered(value: Any) -> Hashable:
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple, set, frozenset)):
            return tuple(sorted(str(item) for item in value))
        return CacheKey._freeze(value)

    def option(self, name: str, default: Any = None) -> Any:
        """Return the normalized value for a cached option."""
        return dict(self.options).get(name, default)


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
                oldest_key = min(self._store, key=lambda k: self._store[k].stored_at)
                del self._store[oldest_key]

    def invalidate_table(
        self,
        base_id: str,
        table_id_or_names: Iterable[str],
    ) -> None:
        """Remove every entry whose key matches the given base + table."""
        table_id_or_names = set(table_id_or_names)
        with self._lock:
            to_remove = [
                k
                for k in self._store
                if k.base_id == base_id and k.table_id_or_name in table_id_or_names
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
                        "formula": key.option("formula", "(all)"),
                        "view": key.option("view", "(default)"),
                        "options": dict(key.options),
                        "age_seconds": round(now - entry.stored_at, 1),
                        "hit_count": entry.hit_count,
                        "record_count": len(entry.records),
                    }
                )
            return {"total_entries": len(entries), "entries": entries}
