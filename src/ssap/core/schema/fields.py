from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Sequence
from ssap.core.schema.registry import get_current_registry

# Allowed OpenAPI/JSON Schema primitive types (OAS 3.1 aligned, simplified)
PRIMITIVES = {"string", "integer", "number", "boolean", "object", "array", "null"}


# ------------------------------------------------------------------------------
# Registry helpers: class -> component name (used by @schema and ref resolution)
# ------------------------------------------------------------------------------


def get_schema_registry():
    """
    Backward-compat shim: returns the current registry's class-name map.
    (Kept for old tests; prefer using registry.get_components() directly.)
    """
    # Construct a proxy dict-like view (read-only)
    return get_current_registry().class_to_name


def register_schema_class(cls: type, name: str | None = None) -> None:
    get_current_registry().register_class_name(cls, name)


def resolve_ref_name(obj):
    return get_current_registry().resolve_name(obj)


# ------------------------------------------------------------------------------
# Ref helper
# ------------------------------------------------------------------------------


class Ref:
    """Represents a $ref to a named component schema."""

    def __init__(self, name: str):
        if not isinstance(name, str) or not name:
            raise ValueError("Ref name must be a non-empty string.")
        self.name = name

    def to_openapi(self) -> Dict[str, Any]:
        return {"$ref": f"#/components/schemas/{self.name}"}

    def __repr__(self) -> str:
        return f"Ref({self.name!r})"


# ------------------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------------------


def _as_type_list(type_: Optional[Union[str, Sequence[str]]]) -> List[str]:
    """Normalize type_ into a list[str] for validation and branching."""
    if type_ is None:
        return []
    if isinstance(type_, str):
        return [type_]
    if isinstance(type_, Sequence):
        vals = list(type_)
        if not vals:
            raise ValueError("type_ list must not be empty.")
        if not all(isinstance(t, str) for t in vals):
            raise TypeError("type_ list must contain only strings.")
        return vals
    raise TypeError("type_ must be a string, a list of strings, or None.")


def _validate_items(items: Any) -> None:
    """
    Strict mode validation for array items.
    - Accepts Ref(...) or a dict schema or a normalized {"$ref": "..."} dict.
    - Dict schema must contain at least "type" OR "$ref".
    - Inline object items are forbidden in strict mode; use Ref('Xxx') or a schema class.
    """
    if isinstance(items, Ref):
        return
    if not isinstance(items, dict):
        raise TypeError("items must be a dict or Ref(...) or a schema class.")
    if "type" not in items and "$ref" not in items:
        raise ValueError("items dict must contain 'type' or '$ref'.")
    if items.get("type") == "object":
        raise ValueError(
            "Inline object in array items is forbidden; use Ref('Xxx') or a schema class."
        )


# ------------------------------------------------------------------------------
# FieldDescriptor
# ------------------------------------------------------------------------------


class FieldDescriptor:
    """
    Descriptor carrying OpenAPI-like metadata for a field (strict mode).
    - Objects MUST be expressed via $ref (no inline object).
    - Arrays may use items=Ref("Xxx") or items={...primitive...} or items=<class> (no inline object).
    - OAS 3.1 union types (e.g., ["string", "null"]) are supported for non-object cases.
    """

    def __init__(
        self,
        *,
        type_: Optional[Union[str, List[str]]] = None,
        description: str = "",
        required: bool = False,
        format_: Optional[str] = None,
        enum: Optional[List[Any]] = None,
        example: Optional[Any] = None,
        default: Any = None,
        items: Optional[Union[Dict[str, Any], Ref, type]] = None,
        # Strict mode: inline object is forbidden; parameters kept for forward-compat but not allowed.
        properties: Optional[Dict[str, Any]] = None,
        required_props: Optional[List[str]] = None,
        # $ref for object fields (string or class)
        ref: Optional[Union[str, type]] = None,
    ):
        """
        Create a field descriptor that carries OpenAPI-like metadata (strict mode).

        Rules (strict):
        - Object fields MUST be expressed via `ref="ComponentName"` or `ref=Class`.
        - Inline object is forbidden (no `properties` / `required_props`).
        - Array items may be Ref("Xxx"), a dict with primitive type, or a schema class;
          inline object in items is forbidden.
        - If `ref` is provided, you MUST NOT set `type_`, `items`, `properties`, or `required_props`.
        - OAS 3.1 union types (e.g., ["string", "null"]) are supported for non-object cases.
        """
        # store name later in __set_name__
        self.name: Optional[str] = None

        # Normalize type_ into list for consistent validation paths.
        type_list = _as_type_list(type_)

        # Short-circuit when ref is provided; other object hints are illegal here.
        if ref is not None:
            if any(x is not None for x in (type_, items, properties, required_props)):
                raise ValueError(
                    "When 'ref' is provided, do not set type_/items/properties/required_props."
                )
            ref_name = resolve_ref_name(ref)
            self.meta: Dict[str, Any] = {
                "ref": ref_name,
                "type": None,
                "description": description,
                "required": required,
                "format": format_,
                "enum": enum,
                "example": example,
                "default": default,
                "items": None,
                "properties": None,
                "required_props": None,
            }
            return  # done

        # No ref path: validate primitive types are allowed.
        unknown = [t for t in type_list if t not in PRIMITIVES]
        if unknown:
            raise ValueError(
                f"Invalid type_ entries: {unknown}. Allowed: {sorted(PRIMITIVES)}"
            )

        # Objects must be modeled via $ref instead of inline schemas.
        if "object" in type_list:
            raise ValueError(
                "Object type is forbidden in strict mode; use 'ref=\"Xxx\"' instead."
            )

        # Arrays must provide items; normalize class items to $ref.
        normalized_items = items
        if "array" in type_list:
            if items is None:
                raise ValueError("Array field must provide 'items'.")
            # normalize class -> {"$ref": "..."} using registry
            if isinstance(items, type):
                normalized_items = {
                    "$ref": f"#/components/schemas/{resolve_ref_name(items)}"
                }
            _validate_items(normalized_items)

        # forbid inline object params entirely
        if properties is not None or required_props is not None:
            raise ValueError(
                "Inline object is forbidden in strict mode (properties/required_props not allowed)."
            )

        # store meta
        self.meta: Dict[str, Any] = {
            "ref": None,
            "type": type_,
            "description": description,
            "required": required,
            "format": format_,
            "enum": enum,
            "example": example,
            "default": default,
            "items": normalized_items,
            "properties": None,
            "required_props": None,
        }

    # preserve declaration order and record the field name
    def __set_name__(self, owner, name):
        self.name = name
        fields = owner.__dict__.get("__schema_fields__")
        if fields is None:
            fields = []
            setattr(owner, "__schema_fields__", fields)
        fields.append(self)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, f"__value__{self.name}", None)

    def __set__(self, instance, value):
        setattr(instance, f"__value__{self.name}", value)

    def to_openapi_property(self) -> Dict[str, Any]:
        """
        Convert the field into an OpenAPI property schema.
        Note: when `ref` is set, we emit only {"$ref": "..."} for maximum compatibility.
        """
        m = self.meta

        # $ref-only object; no other keywords allowed here.
        if m.get("ref"):
            return {"$ref": f"#/components/schemas/{m['ref']}"}

        schema: Dict[str, Any] = {}
        if m["type"] is not None:
            schema["type"] = m["type"]
        if m["format"]:
            schema["format"] = m["format"]
        if m["description"]:
            schema["description"] = m["description"]
        if m["enum"] is not None:
            schema["enum"] = m["enum"]
        if m["example"] is not None:
            schema["example"] = m["example"]
        if m["default"] is not None:
            schema["default"] = m["default"]

        # array branch
        type_list = _as_type_list(m["type"])
        if "array" in type_list:
            items = m["items"]
            if isinstance(items, Ref):
                schema["items"] = items.to_openapi()
            else:
                schema["items"] = items

        return schema


def field(**kwargs) -> FieldDescriptor:
    """
    Public factory for FieldDescriptor (strict mode with $ref support).
    Examples:
        # scalar
        name = field(type_="string", required=True, description="Username")

        # array of strings
        tags = field(type_="array", items={"type": "string"})

        # object via $ref (string)
        owner = field(ref="User")

        # object via $ref (class)
        # owner = field(ref=User)

        # array of object via $ref (class)
        # members = field(type_="array", items=User)
    """
    return FieldDescriptor(**kwargs)


# ------------------------------------------------------------------------------
# A tiny helper to preview a class schema BEFORE @schema (handy for tests)
# ------------------------------------------------------------------------------


def _preview_object_schema(cls) -> Dict[str, Any]:
    """
    Build a minimal OpenAPI object schema from a class that uses FieldDescriptor,
    without needing the @schema decorator (handy for early testing).
    """
    properties: Dict[str, Any] = {}
    required: List[str] = []
    fields: List[FieldDescriptor] = getattr(cls, "__schema_fields__", [])
    for f in fields:
        properties[f.name] = f.to_openapi_property()
        if f.meta.get("required"):
            required.append(f.name)

    schema: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema
