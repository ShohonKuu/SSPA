from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type
from contextlib import contextmanager
import contextvars

from .model import PathItem


@dataclass
class PathRecord:
    item: PathItem = field(default_factory=PathItem)
    classes: List[Type] = field(default_factory=list)


class PathRegistry:
    """
    Holds OpenAPI path items keyed by absolute path url and the classes
    decorated by @path for that url.
    """

    def __init__(self) -> None:
        self._map: Dict[str, PathRecord] = {}

    def ensure(self, url: str) -> PathRecord:
        rec = self._map.get(url)
        if rec is None:
            rec = PathRecord()
            self._map[url] = rec
        return rec

    def add_class(self, url: str, cls: Type) -> None:
        rec = self.ensure(url)
        rec.classes.append(cls)

    def get(self, url: str) -> Optional[PathRecord]:
        return self._map.get(url)

    def all(self) -> Dict[str, PathRecord]:
        return self._map

    def clear(self) -> None:
        self._map.clear()


# Context-variable-backed "current" path registry
_current_path_registry: contextvars.ContextVar[PathRegistry] = contextvars.ContextVar(
    "current_path_registry", default=PathRegistry()
)


def get_current_path_registry() -> PathRegistry:
    return _current_path_registry.get()


def set_current_path_registry(reg: PathRegistry) -> None:
    _current_path_registry.set(reg)


@contextmanager
def use_path_registry(reg: PathRegistry):
    """
    Temporarily switch the current path registry within the context.
    """
    token = _current_path_registry.set(reg)
    try:
        yield reg
    finally:
        _current_path_registry.reset(token)
