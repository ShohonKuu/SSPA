from __future__ import annotations
from typing import Any, Dict, Sequence, Type, Optional

import yaml

from sspa.core.schema.decorator import schema, get_components_registry
from sspa.core.schema.registry import SchemaRegistry, use_registry


def to_yaml(data: Dict[str, Any]) -> str:
    """
    Convert a Python dict to a human-friendly YAML string.

    - Uses safe_dump to avoid arbitrary Python tags.
    - Keeps insertion order for readability.
    - Block style for better diffs/reviews.
    """
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


def _ensure_registered(cls: Type, reg: SchemaRegistry) -> None:
    """
    Ensure `cls` has been registered into `reg` as a component schema.
    If not, decorate it with @schema(registry=reg).
    Safe to call multiple times.
    """
    # Fast path: if a class already has a __schema_name__ that exists in reg, skip.
    comp_name = getattr(cls, "__schema_name__", None) or cls.__name__
    if comp_name in reg.get_components():
        return

    # Decorate into target registry, preserving any custom component name.
    schema(name=comp_name, registry=reg)(cls)


def build_components_schemas(
    classes: Sequence[Type],
    *,
    registry: Optional[SchemaRegistry] = None,
) -> Dict[str, Any]:
    """
    Build a dict of the form:
      { "components": { "schemas": { <Name>: <Schema>, ... } } }

    - Registers all provided classes into a fresh or given registry.
    - Does NOT include 'openapi', 'info', or 'paths'. This is intentionally
      schema-only for large projects where schemas and paths are managed separately.
    """
    reg = registry or SchemaRegistry()
    with use_registry(reg):
        for cls in classes:
            _ensure_registered(cls, reg)
        # Reuse current-registry accessor to get the live mapping
        return {"components": {"schemas": get_components_registry()}}


def export_schema_yaml(
    classes: Sequence[Type],
    *,
    registry: Optional[SchemaRegistry] = None,
) -> str:
    """
    Convenience one-shot that returns a YAML string for:
      components:
        schemas:
          ...
    """
    doc = build_components_schemas(classes, registry=registry)
    return to_yaml(doc)
