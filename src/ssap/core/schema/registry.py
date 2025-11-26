# src/ssap/core/schema/registry.py
from __future__ import annotations
from typing import Any, Dict, Optional, Type
from contextlib import contextmanager
import contextvars


class SchemaRegistry:
    """
    Holds:
      - components: component-name -> schema dict (OpenAPI components.schemas)
      - class_to_name: python class -> component-name (for $ref resolution)
    """

    def __init__(self) -> None:
        self.components: Dict[str, Dict[str, Any]] = {}
        self.class_to_name: Dict[Type, str] = {}

    # ---- class-name mapping ----
    def register_class_name(self, cls: Type, name: Optional[str] = None) -> str:
        comp = name or cls.__name__
        self.class_to_name[cls] = comp
        return comp

    def resolve_name(self, obj: Type | str) -> str:
        if isinstance(obj, str):
            return obj
        if isinstance(obj, type):
            if obj in self.class_to_name:
                return self.class_to_name[obj]
            # Fall back to a stored schema alias if present (e.g., from @schema(name="Alias"))
            return getattr(obj, "__schema_name__", obj.__name__)
        raise TypeError("Expected a class or string for ref resolution.")

    # ---- components ----
    def put_component(self, name: str, schema_dict: Dict[str, Any]) -> None:
        self.components[name] = schema_dict

    def get_components(self) -> Dict[str, Dict[str, Any]]:
        return self.components

    def clear(self) -> None:
        self.components.clear()
        self.class_to_name.clear()

    # Optional helpers
    def snapshot(self) -> Dict[str, Any]:
        return {"components": {"schemas": dict(self.components)}}


# A context-variable-backed "current" registry
_current_registry: contextvars.ContextVar[SchemaRegistry] = contextvars.ContextVar(
    "current_schema_registry", default=SchemaRegistry()
)


def get_current_registry() -> SchemaRegistry:
    return _current_registry.get()


def set_current_registry(reg: SchemaRegistry) -> None:
    _current_registry.set(reg)


@contextmanager
def use_registry(reg: SchemaRegistry):
    """
    Temporarily switch the current registry within the context.
    """
    token = _current_registry.set(reg)
    try:
        yield reg
    finally:
        _current_registry.reset(token)
