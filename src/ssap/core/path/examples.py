from __future__ import annotations
from typing import Any, Dict, List, Type


def ex(schema_class: Type, /, **kwargs) -> Dict[str, Any]:
    """Explicitly construct an example dict for a @schema class. (stub)"""
    return dict(kwargs)


def auto_ex(
    schema_class: Type, *, overrides: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Auto-generate an example dict based on @schema metadata. (stub)"""
    base = {}  # TODO: synthesize from schema meta
    if overrides:
        # naive shallow merge for stub
        base.update(overrides)
    return base


def ex_list(
    schema_class: Type, *, n: int = 2, overrides: List[Dict[str, Any]] | None = None
) -> List[Dict[str, Any]]:
    """Build a list of examples. (stub)"""
    items: List[Dict[str, Any]] = []
    for i in range(n):
        ov = overrides[i] if overrides and i < len(overrides) else {}
        items.append(auto_ex(schema_class, overrides=ov))
    return items
