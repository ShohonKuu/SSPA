from __future__ import annotations
from typing import Any, Dict, Optional, Type

from ssap.core.schema.fields import _preview_object_schema
from ssap.core.schema.registry import get_current_registry, SchemaRegistry

__all__ = ["schema", "get_components_registry"]


def get_components_registry() -> Dict[str, Dict[str, Any]]:
    """
    Return the current registry's OpenAPI components.schemas dict.

    Notes
    -----
    - This is a backward-compatible accessor so callers can keep using
      the old name without touching the registry directly.
    - The returned dict is the *live* mapping managed by the current registry.
      Mutations will be visible globally within the same registry context.
    """
    return get_current_registry().get_components()


def schema(
    _cls: Optional[Type] = None,
    *args,
    name: Optional[str] = None,
    registry: Optional[SchemaRegistry] = None,
):
    """
    Class decorator that:
      1) Builds an object schema from FieldDescriptor metadata.
      2) Registers (class -> component name) for $ref resolution.
      3) Registers (component name -> schema dict) into the registry.

    Supported usages
    ----------------
    @schema
    class A: ...

    @schema()
    class B: ...

    @schema("Custom")          # positional component name
    class C: ...

    @schema(name="Custom")     # keyword component name
    class D: ...

    Parameters
    ----------
    _cls : Optional[Type]
        The decorated class when using bare @schema. None when used as @schema(...).

    *args :
        Extra positional arguments. If the first positional argument is a string,
        it is treated as the component name (e.g., @schema("Name")).

    name : Optional[str]
        Component name override (e.g., @schema(name="Name")).

    registry : Optional[SchemaRegistry]
        Optional explicit registry to register into. If not provided, the
        current registry from get_current_registry() is used.

    Behavior
    --------
    - If both a positional name and 'name=' are provided, a ValueError is raised.
    - The class will receive two convenience attributes:
        - __schema_name__: the resolved component name
        - __openapi_schema__: the generated object schema dict
    """
    # Support @schema("CustomName"): treat first positional str as component name.
    positional_name: Optional[str] = None
    if _cls is not None and isinstance(_cls, str):
        positional_name = _cls
        _cls = None  # convert into decorator factory mode

    if positional_name is not None and name is not None:
        raise ValueError(
            "schema(): do not pass both a positional name and name= simultaneously."
        )
    effective_name = name or positional_name

    reg = registry or get_current_registry()

    def _decorate(cls: Type) -> Type:
        comp_name = effective_name or cls.__name__

        # 1) Build object-level schema from FieldDescriptor metadata.
        obj_schema = _preview_object_schema(cls)

        # 2) Register class -> component name (used by ref=Class / items=Class).
        reg.register_class_name(cls, comp_name)

        # 3) Register component name -> schema dict.
        reg.put_component(comp_name, obj_schema)

        # Convenience/debugging hooks on the class.
        cls.__schema_name__ = comp_name
        cls.__openapi_schema__ = obj_schema
        return cls

    # Bare decorator usage: @schema
    if _cls is not None:
        return _decorate(_cls)

    # Decorator factory usage: @schema(...), @schema("Name"), @schema(name="Name")
    return _decorate
