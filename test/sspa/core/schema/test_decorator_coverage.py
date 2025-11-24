import pytest

from sspa.core.schema.decorator import schema, get_components_registry
from sspa.core.schema.registry import get_current_registry
from sspa.core.schema.fields import (
    field,
    get_schema_registry as get_fields_registry,
)


@pytest.fixture(autouse=True)
def _reset_registries():
    """Reset both the class->name map and the components registry."""
    setattr(get_fields_registry, "_registry", {})
    get_current_registry().clear()
    yield
    setattr(get_fields_registry, "_registry", {})
    get_current_registry().clear()


def test_components_registry_singleton_and_mutation_visibility():
    """get_components_registry returns the same dict object; mutations are shared."""
    comp_a = get_components_registry()
    comp_b = get_components_registry()
    assert comp_a is comp_b
    comp_a["X"] = {"type": "object", "properties": {}}
    assert "X" in comp_b


def test_schema_decorator_default_name_registers_class_and_schema():
    """@schema() with default name uses class.__name__, registers class->name and name->schema."""

    @schema()
    class User:
        id = field(type_="integer", required=True, description="User ID")
        name = field(type_="string", required=True, description="Full name")
        email = field(type_=["string", "null"], description="Email or null")

    comps = get_components_registry()
    assert "User" in comps
    user_schema = comps["User"]
    assert user_schema["type"] == "object"
    assert set(user_schema.get("required", [])) == {"id", "name"}
    assert user_schema["properties"]["name"]["description"] == "Full name"
    assert getattr(User, "__schema_name__") == "User"
    assert isinstance(getattr(User, "__openapi_schema__"), dict)


def test_schema_decorator_custom_name_overrides_component_name():
    """@schema('Custom') should register using the provided component name instead of class name."""

    @schema("CustomUser")
    class User2:
        uid = field(type_="integer", required=True)
        nick = field(type_="string")

    comps = get_components_registry()
    assert "CustomUser" in comps
    assert "User2" not in comps
    assert getattr(User2, "__schema_name__") == "CustomUser"


def test_schema_decorator_resolves_ref_and_array_items_class():
    """Decorating referenced classes first should allow ref=Class and items=Class."""

    @schema()
    class User:
        id = field(type_="integer", required=True)
        name = field(type_="string", required=True)

    @schema()
    class Team:
        owner = field(ref=User, required=True, description="Team owner")
        members = field(type_="array", items=User, description="Team members")

    comps = get_components_registry()
    assert "User" in comps and "Team" in comps
    team_schema = comps["Team"]
    assert team_schema["properties"]["owner"] == {"$ref": "#/components/schemas/User"}
    assert team_schema["properties"]["members"]["items"] == {
        "$ref": "#/components/schemas/User"
    }
    assert set(team_schema.get("required", [])) == {"owner"}


def test_schema_decorator_multiple_classes_and_registry_is_shared():
    """Multiple decorated classes should accumulate in the same components registry dict."""

    @schema()
    class A:
        x = field(type_="integer")

    @schema()
    class B:
        y = field(type_="string")

    comps = get_components_registry()
    assert set(comps.keys()) >= {"A", "B"}
    assert comps["A"]["properties"]["x"]["type"] == "integer"
    assert comps["B"]["properties"]["y"]["type"] == "string"


def test_schema_decorator_custom_name_positional_and_conflict():
    """Positional name works; conflict with name= raises."""

    @schema("CustomUser2")
    class U:
        a = field(type_="string")

    comps = get_components_registry()
    assert "CustomUser2" in comps and "U" not in comps

    with pytest.raises(ValueError):

        @schema("X", name="Y")
        class Bad:
            p = field(type_="integer")
