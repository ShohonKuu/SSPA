# tests/test_fields_coverage.py
# Purpose: Achieve 100% coverage for sspa.core.schema.fields.
# Notes:
# - All comments/docstrings are in English as requested.
# - The tests assume your package is installed in editable mode (pip install -e .).

import pytest

import sspa.core.schema.fields as fmod
from sspa.core.schema.fields import (
    FieldDescriptor,
    Ref,
    field,
    register_schema_class,
    get_schema_registry,
    resolve_ref_name,
    _preview_object_schema,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    """Ensure the global class->name registry is reset before each test."""
    # The registry is stored as an attribute on the function object.
    setattr(get_schema_registry, "_registry", {})
    yield
    setattr(get_schema_registry, "_registry", {})


# ----------------------------- Helpers coverage -----------------------------


def test_as_type_list_happy_paths():
    """_as_type_list: cover string, list[str], and None cases."""
    assert fmod._as_type_list("string") == ["string"]
    assert fmod._as_type_list(["string", "null"]) == ["string", "null"]
    assert fmod._as_type_list(None) == []


def test_as_type_list_errors():
    """_as_type_list: cover empty list, non-string elements, and wrong types."""
    with pytest.raises(ValueError):
        fmod._as_type_list([])  # empty list not allowed
    with pytest.raises(TypeError):
        fmod._as_type_list(["string", 1])  # non-string element
    with pytest.raises(TypeError):
        fmod._as_type_list(123)  # wrong type entirely


def test_validate_items_accepts_and_rejects():
    """_validate_items: accept Ref, dict with 'type' or '$ref'; reject others."""
    # Accept Ref
    fmod._validate_items(Ref("X"))
    # Accept dict with type
    fmod._validate_items({"type": "string"})

    # Accept dict with $ref
    fmod._validate_items({"$ref": "#/components/schemas/X"})

    # Reject non-dict non-Ref
    with pytest.raises(TypeError):
        fmod._validate_items("not-a-dict-or-ref")

    # Reject dict missing 'type' and '$ref'
    with pytest.raises(ValueError):
        fmod._validate_items({})

    # Reject inline object in items (strict mode)
    with pytest.raises(ValueError):
        fmod._validate_items({"type": "object"})


# ----------------------------- Registry & Ref -------------------------------


def test_register_and_resolve_ref_name_string_and_class():
    """resolve_ref_name: string passthrough; class uses registry or fallback to __name__."""
    # String passthrough
    assert resolve_ref_name("User") == "User"

    # Class without registration should fallback to __name__
    class Ghost:
        pass

    assert resolve_ref_name(Ghost) == "Ghost"

    # After registration, should use registered name
    class Owner:
        pass

    register_schema_class(Owner, "OwnerAlias")
    assert resolve_ref_name(Owner) == "OwnerAlias"


def test_ref_object_to_openapi_and_repr():
    """Ref: constructor validation, to_openapi(), and __repr__."""
    r = Ref("User")
    assert r.to_openapi() == {"$ref": "#/components/schemas/User"}
    assert "Ref('User')" in repr(r)

    with pytest.raises(ValueError):
        Ref("")  # must be non-empty


# ------------------------ FieldDescriptor: happy paths -----------------------


def test_fielddescriptor_scalar_and_to_openapi_property():
    """Scalar field: verify emitted keywords (type, format, description, enum, example, default)."""
    fd = FieldDescriptor(
        type_="string",
        description="Username",
        required=True,  # object-level (collected elsewhere)
        format_="email",
        enum=["a", "b"],
        example="john@example.com",
        default="john@example.com",
    )
    prop = fd.to_openapi_property()
    assert prop["type"] == "string"
    assert prop["format"] == "email"
    assert prop["description"] == "Username"
    assert prop["enum"] == ["a", "b"]
    assert prop["example"] == "john@example.com"
    assert prop["default"] == "john@example.com"


def test_fielddescriptor_with_ref_string_path():
    """Object field via ref='X': should emit only $ref and disallow mixing with type/items/etc."""
    fd = FieldDescriptor(ref="User", description="ignored at ref-node")
    prop = fd.to_openapi_property()
    assert prop == {"$ref": "#/components/schemas/User"}

    # Mixing 'ref' with other keywords is forbidden
    with pytest.raises(ValueError):
        FieldDescriptor(ref="User", type_="object")
    with pytest.raises(ValueError):
        FieldDescriptor(ref="User", items={"type": "string"})
    with pytest.raises(ValueError):
        FieldDescriptor(ref="User", properties={})
    with pytest.raises(ValueError):
        FieldDescriptor(ref="User", required_props=[])


def test_fielddescriptor_with_ref_class_path():
    """Object field via ref=Class: auto-resolve to registered component name, or fallback to __name__."""

    class User:
        pass

    # If not registered, fallback to class.__name__
    fd1 = FieldDescriptor(ref=User)
    assert fd1.to_openapi_property() == {"$ref": "#/components/schemas/User"}

    # After registration, use the registered alias
    register_schema_class(User, "UserAlias")
    fd2 = FieldDescriptor(ref=User)
    assert fd2.to_openapi_property() == {"$ref": "#/components/schemas/UserAlias"}


def test_fielddescriptor_array_items_variants_and_dict_normalization():
    """Array field: items can be dict with primitive type, Ref, or class (normalized to $ref)."""
    # items as dict with primitive type
    fd1 = FieldDescriptor(type_="array", items={"type": "string"})
    assert fd1.to_openapi_property() == {"type": "array", "items": {"type": "string"}}

    # items as Ref
    fd2 = FieldDescriptor(type_="array", items=Ref("User"))
    assert fd2.to_openapi_property() == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/User"},
    }

    # items as class (should normalize to {"$ref": ...}); with fallback and with registry
    class Owner:
        pass

    # no registry -> fallback to Owner
    fd3 = FieldDescriptor(type_="array", items=Owner)
    assert fd3.to_openapi_property() == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/Owner"},
    }

    # after registry -> use alias
    register_schema_class(Owner, "OwnerAlias")
    fd4 = FieldDescriptor(type_="array", items=Owner)
    assert fd4.to_openapi_property() == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/OwnerAlias"},
    }


def test_fielddescriptor_set_name_and_descriptor_get_set():
    """__set_name__ should record declaration order; __get__/__set__ should store per-instance value."""

    class Demo:
        a = field(type_="string")
        b = field(type_="integer")

    # Declaration order
    names = [fd.name for fd in getattr(Demo, "__schema_fields__", [])]
    assert names == ["a", "b"]

    # Descriptor get/set
    d = Demo()
    d.a = "alice"
    d.b = 42
    assert d.a == "alice"
    assert d.b == 42


def test_field_factory_is_simple_wrapper():
    """field() should return a FieldDescriptor with given metadata."""
    fd = field(type_="number", description="A number")
    assert isinstance(fd, FieldDescriptor)
    assert fd.to_openapi_property()["type"] == "number"


def test_preview_object_schema_collects_required_and_properties():
    """_preview_object_schema should build properties and object-level 'required' list."""

    class User:
        id = field(type_="integer", required=True, description="User ID")
        name = field(type_="string", required=True, description="Full name")
        email = field(type_=["string", "null"], description="Nullable email")
        tags = field(type_="array", items={"type": "string"}, description="String tags")

    schema = _preview_object_schema(User)
    assert schema["type"] == "object"
    assert set(schema["required"]) == {"id", "name"}
    props = schema["properties"]
    assert props["id"]["type"] == "integer"
    assert props["name"]["description"] == "Full name"
    assert props["email"]["type"] == ["string", "null"]
    assert props["tags"]["items"] == {"type": "string"}


# ------------------------ FieldDescriptor: error paths -----------------------


def test_invalid_type_entries_raise():
    """Invalid primitive entries in type_ should raise ValueError."""
    with pytest.raises(ValueError):
        FieldDescriptor(type_="text")  # not in PRIMITIVES

    with pytest.raises(ValueError):
        FieldDescriptor(type_=["string", "weird"])  # mixed, contains invalid


def test_object_type_forbidden_in_strict_mode():
    """Strict mode forbids inline object entirely; must use ref='Xxx'."""
    with pytest.raises(ValueError):
        FieldDescriptor(type_="object")


def test_inline_object_params_forbidden_even_if_type_is_not_object():
    """Strict mode forbids properties/required_props regardless of type (no inline object)."""
    with pytest.raises(ValueError):
        FieldDescriptor(type_="string", properties={"a": {"type": "string"}})
    with pytest.raises(ValueError):
        FieldDescriptor(type_="string", required_props=["a"])


def test_array_requires_items_and_rejects_bad_items():
    """Array: items is required; must be dict|Ref|class; dict must have 'type' or '$ref'."""
    with pytest.raises(ValueError):
        FieldDescriptor(type_="array")  # missing items

    with pytest.raises(TypeError):
        FieldDescriptor(type_="array", items="string")  # wrong type

    with pytest.raises(ValueError):
        FieldDescriptor(type_="array", items={})  # dict missing keys

    # Inline object in items is forbidden
    with pytest.raises(ValueError):
        FieldDescriptor(type_="array", items={"type": "object"})


def test_register_schema_class_creates_registry_when_missing():
    """register_schema_class: cover branch where the internal registry does not exist yet."""
    # Ensure attribute is not present to hit the 'create new dict' branch.
    if hasattr(get_schema_registry, "_registry"):
        delattr(get_schema_registry, "_registry")

    class Foo: ...

    register_schema_class(Foo, "FooAlias")

    reg = get_schema_registry()
    assert isinstance(reg, dict)
    assert reg.get(Foo) == "FooAlias"


def test_resolve_ref_name_raises_for_invalid_type():
    """resolve_ref_name: raise TypeError when neither str nor class is given."""
    with pytest.raises(TypeError):
        resolve_ref_name(123)  # not a str or type


def test_preview_object_schema_without_required_key():
    """_preview_object_schema: when no field is required, the schema should not include 'required'."""

    class OptionalOnly:
        a = field(type_="string", description="not required")
        b = field(type_="number", description="also not required")

    schema = fmod._preview_object_schema(OptionalOnly)
    assert schema["type"] == "object"
    assert "required" not in schema  # no required list emitted


def test_descriptor_get_returns_none_when_unset():
    """FieldDescriptor.__get__: reading a field before any assignment should return None."""

    class Demo:
        x = field(type_="integer")

    d = Demo()
    # No assignment yet; should be None
    assert d.x is None


def test_descriptor_get_on_class_returns_descriptor():
    """Accessing the descriptor via the class should return the FieldDescriptor itself."""

    class Demo:
        x = field(type_="string")

    # Access on class hits FieldDescriptor.__get__(instance=None, owner=Demo)
    assert isinstance(Demo.x, FieldDescriptor)


def test_type_null_only_and_union_order_is_preserved():
    """Cover the 'null' primitive and verify union order is preserved."""
    fd_null = FieldDescriptor(type_="null", description="pure null")
    assert fd_null.to_openapi_property()["type"] == "null"

    # Union order should be exactly as provided
    fd_union = FieldDescriptor(type_=["null", "string"])
    assert fd_union.to_openapi_property()["type"] == ["null", "string"]


# ------------------------------- Inheritance ---------------------------------


def test_schema_fields_are_per_class_and_preserve_order_with_inheritance():
    """
    Ensure __schema_fields__ exists per-class (not shared) and preserves declaration order
    when using inheritance. Base class fields should not leak into subclass' list unless
    redeclared on the subclass.
    """

    class Base:
        a = field(type_="string")
        b = field(type_="integer")

    class Child(Base):
        # only new fields declared here should appear in Child.__schema_fields__
        c = field(type_="boolean")

    # Base has its own schema fields
    base_names = [fd.name for fd in getattr(Base, "__schema_fields__", [])]
    assert base_names == ["a", "b"]

    # Child has only the fields declared on Child class body
    child_names = [fd.name for fd in getattr(Child, "__schema_fields__", [])]
    assert child_names == ["c"]

    # Preview schemas reflect the same
    base_schema = _preview_object_schema(Base)
    child_schema = _preview_object_schema(Child)
    assert set(base_schema["properties"].keys()) == {"a", "b"}
    assert set(child_schema["properties"].keys()) == {"c"}


# -------------------------- Instances isolation ------------------------------


def test_descriptor_values_are_isolated_per_instance():
    """Setting a descriptor value on one instance must not affect another instance."""

    class Demo:
        x = field(type_="string")
        y = field(type_="integer")

    d1, d2 = Demo(), Demo()
    d1.x, d1.y = "alice", 10
    d2.x, d2.y = "bob", 20

    assert (d1.x, d1.y) == ("alice", 10)
    assert (d2.x, d2.y) == ("bob", 20)


# ------------------------ Registry default-name branch -----------------------


def test_register_schema_class_default_name_and_registry_object_identity():
    """
    When name is not provided to register_schema_class, it should fall back to class.__name__.
    Also verify get_schema_registry() returns the same dict object on subsequent calls.
    """

    class Foo:
        pass

    register_schema_class(Foo)  # no custom name -> use "Foo"
    reg1 = get_schema_registry()
    reg2 = get_schema_registry()
    assert reg1 is reg2
    assert reg1.get(Foo) == "Foo"


# ----------------------------- items validation ------------------------------


def test_validate_items_accepts_extra_keys_and_rejects_inline_object():
    """
    _validate_items should accept dicts that contain type plus extra keys (permissive),
    and still reject inline object type in items.
    """
    # Extra keys are allowed (e.g., a format for strings)
    fmod._validate_items({"type": "string", "format": "email"})

    # Inline object remains forbidden
    with pytest.raises(ValueError):
        fmod._validate_items(
            {"type": "object", "properties": {"a": {"type": "string"}}}
        )


# ------------------------------- Misc sanity ---------------------------------


def test_field_factory_with_all_optional_kwargs_omitted():
    """field() should work with minimal kwargs for a primitive type."""
    fd = field(type_="boolean")
    assert isinstance(fd, FieldDescriptor)
    assert fd.to_openapi_property()["type"] == "boolean"
