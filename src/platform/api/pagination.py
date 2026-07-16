"""Pagination primitives (Module 10).

Both classic offset/limit pagination (:class:`Page`) and opaque cursor
pagination (:class:`CursorPage`) are supported. Cursors are base64-encoded
offsets — opaque to clients, so the underlying strategy can change without
breaking pagination contracts.
"""

from __future__ import annotations

import base64
from typing import Generic, Sequence, TypeVar

from pydantic import Field

from src.platform.common.models import PlatformModel

T = TypeVar("T")

MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 25


class PageRequest(PlatformModel):
    """An offset/limit page request (clamped to sane bounds)."""

    page: int = 1
    size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        """Return the zero-based offset for this request."""
        return max(0, (max(1, self.page) - 1) * self._size())

    def _size(self) -> int:
        """Return the clamped page size."""
        return max(1, min(self.size, MAX_PAGE_SIZE))


class Page(PlatformModel, Generic[T]):
    """A single page of results plus navigation metadata."""

    items: list[T] = Field(default_factory=list)
    page: int = 1
    size: int = DEFAULT_PAGE_SIZE
    total: int = 0

    @property
    def total_pages(self) -> int:
        """Return the total number of pages."""
        size = max(1, self.size)
        return (self.total + size - 1) // size

    @property
    def has_next(self) -> bool:
        """Return whether a next page exists."""
        return self.page < self.total_pages


def paginate(items: Sequence[T], request: PageRequest) -> Page:
    """Return the requested offset page over ``items``."""
    size = max(1, min(request.size, MAX_PAGE_SIZE))
    start = request.offset
    window = list(items[start : start + size])
    return Page(items=window, page=max(1, request.page), size=size, total=len(items))


# -- cursor pagination ------------------------------------------------------


def encode_cursor(offset: int) -> str:
    """Encode an integer offset as an opaque base64 cursor."""
    return base64.urlsafe_b64encode(f"o:{offset}".encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str | None) -> int:
    """Decode an opaque cursor back to an offset (0 if empty/invalid)."""
    if not cursor:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        if raw.startswith("o:"):
            return max(0, int(raw[2:]))
    except (ValueError, UnicodeDecodeError):
        return 0
    return 0


class CursorPage(PlatformModel, Generic[T]):
    """A cursor-paginated slice with a forward ``next_cursor``."""

    items: list[T] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False


def cursor_paginate(
    items: Sequence[T], *, cursor: str | None = None, size: int = DEFAULT_PAGE_SIZE
) -> CursorPage:
    """Return a cursor page over ``items`` starting after ``cursor``."""
    size = max(1, min(size, MAX_PAGE_SIZE))
    start = decode_cursor(cursor)
    window = list(items[start : start + size])
    has_more = start + size < len(items)
    next_cursor = encode_cursor(start + size) if has_more else None
    return CursorPage(items=window, next_cursor=next_cursor, has_more=has_more)
