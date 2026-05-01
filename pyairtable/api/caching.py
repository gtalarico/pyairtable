"""
Request-level caching for Airtable API calls.

This module provides configurable, TTL-based caching of record fetch operations.
Caching is opt-in and is disabled by default.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from pyairtable.api.types import RecordDict

if TYPE_CHECKING:
    pass

__all__ = ["CacheEntry", "TableTTLConfig", "RequestCache"]


@dataclass
class CacheEntry:
    """A single cached record set with metadata."""

    records: List[RecordDict]
    stored_at_seconds: float
    hit_count: int = 0


@dataclass(frozen=True)
class TableTTLConfig:
    """Configuration for per-table TTL (time-to-live) values."""

    default_ttl_seconds: int = 300
    overrides: Dict[str, int] = field(default_factory=dict)

    def ttl_for_table(self, table_name: str) -> int:
        """Get the TTL for a specific table."""
        return self.overrides.get(table_name, self.default_ttl_seconds)


CacheKey = Tuple[str, str, str, str, Tuple[str, ...], str, Tuple[str, ...], bool]


class RequestCache:
    """
    Thread-safe, TTL-based cache for table record fetches.

    Cache keys are tuples of (base_id, table_id_or_name, formula, cell_format,
    fields, view, sort, use_field_ids).
    """

    def __init__(self, ttl_config: TableTTLConfig) -> None:
        """Initialize the cache with a TTL configuration."""
        self._store: Dict[CacheKey, CacheEntry] = {}
        self._lock = threading.Lock()
        self._ttl_config = ttl_config

    def get_entry(self, key: CacheKey) -> Optional[List[RecordDict]]:
        """
        Retrieve a cached entry if it exists and has not expired.

        Returns None if the entry doesn't exist or has expired.
        """
        table_name = key[1]
        ttl = self._ttl_config.ttl_for_table(table_name)

        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            age = time.monotonic() - entry.stored_at_seconds
            if age > ttl:
                del self._store[key]
                return None

            entry.hit_count += 1
            return entry.records

    def put_entry(self, key: CacheKey, records: List[RecordDict]) -> None:
        """Store a cache entry."""
        entry = CacheEntry(records=records, stored_at_seconds=time.monotonic())
        with self._lock:
            self._store[key] = entry

    def invalidate_table(self, base_id: str, table_name: str) -> None:
        """Remove all cache entries for a specific table."""
        with self._lock:
            keys_to_remove = [
                k for k in self._store if k[0] == base_id and k[1] == table_name
            ]
            for k in keys_to_remove:
                del self._store[k]

    def invalidate_all(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._store.clear()

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics for debugging."""
        with self._lock:
            now = time.monotonic()
            entries = []
            for key, entry in self._store.items():
                entries.append(
                    {
                        "base_id": key[0],
                        "table": key[1],
                        "formula": key[2] or "(all)",
                        "cell_format": key[3] or "json",
                        "fields": key[4] or "(all)",
                        "view": key[5] or "(default)",
                        "sort": key[6] or "(none)",
                        "use_field_ids": key[7],
                        "age_seconds": round(now - entry.stored_at_seconds, 1),
                        "hit_count": entry.hit_count,
                        "record_count": len(entry.records),
                    }
                )
            return {"total_entries": len(entries), "entries": entries}
