"""Filtering and sorting specifications (Module 10).

Declarative, transport-agnostic filter and sort specs that the future REST
layer can parse from query strings and apply uniformly over any list of
pydantic models — no per-endpoint filtering code.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Sequence, TypeVar

from src.platform.common.models import PlatformModel

T = TypeVar("T")


class Operator(str, Enum):
    """Supported filter comparison operators."""

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    CONTAINS = "contains"
    IN = "in"


class FilterSpec(PlatformModel):
    """A single field/operator/value filter clause."""

    field: str
    op: Operator = Operator.EQ
    value: Any = None


class SortSpec(PlatformModel):
    """A field + direction sort clause."""

    field: str
    descending: bool = False


def _get(obj: Any, field: str) -> Any:
    """Read a field from a pydantic model, dict or object."""
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)


def _matches(obj: Any, spec: FilterSpec) -> bool:
    """Return whether ``obj`` satisfies a single filter clause."""
    actual = _get(obj, spec.field)
    target = spec.value
    if spec.op == Operator.EQ:
        return actual == target
    if spec.op == Operator.NE:
        return actual != target
    if actual is None:
        return False
    if spec.op == Operator.LT:
        return actual < target
    if spec.op == Operator.LTE:
        return actual <= target
    if spec.op == Operator.GT:
        return actual > target
    if spec.op == Operator.GTE:
        return actual >= target
    if spec.op == Operator.CONTAINS:
        return str(target).lower() in str(actual).lower()
    if spec.op == Operator.IN:
        return actual in (target or [])
    return False


def apply_filters(items: Sequence[T], filters: Sequence[FilterSpec]) -> list[T]:
    """Return items satisfying *all* filter clauses (logical AND)."""
    return [obj for obj in items if all(_matches(obj, f) for f in filters)]


def apply_sorts(items: Sequence[T], sorts: Sequence[SortSpec]) -> list[T]:
    """Return items sorted by the given clauses (later clauses break ties)."""
    result = list(items)
    for spec in reversed(sorts):
        result.sort(
            key=lambda o, f=spec.field: (_get(o, f) is None, _get(o, f)),
            reverse=spec.descending,
        )
    return result
