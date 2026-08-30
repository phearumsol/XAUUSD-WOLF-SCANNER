"""Replaceable in-memory cache for one refresh cycle."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


class RefreshCache:
    """Cache values by key until the current dashboard refresh completes."""

    def __init__(self) -> None:
        self._items: dict[object, object] = {}

    def get_or_load(self, key: object, loader: Callable[[], T]) -> T:
        """Return a cached value or populate it from ``loader``."""
        if key not in self._items:
            self._items[key] = loader()
        return self._items[key]  # type: ignore[return-value]

    def clear(self) -> None:
        """Clear values before a new refresh cycle."""
        self._items.clear()