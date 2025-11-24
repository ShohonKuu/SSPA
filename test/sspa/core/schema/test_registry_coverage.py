import pytest

from sspa.core.schema.registry import (
    SchemaRegistry,
    get_current_registry,
    set_current_registry,
    use_registry,
)

# ------------------------------ SchemaRegistry core ------------------------------


def test_initial_state_and_getters_are_empty_and_live():
    """A new registry starts empty; get_components returns the live dict."""
    reg = SchemaRegistry()
    assert reg.get_components() == {}
    # live dict property: identity and mutations are visible
    comps = reg.get_components()
    assert comps is reg.get_components()
    comps["X"] = {"type": "object", "properties": {}}
    assert "X" in reg.get_components()


def test_register_class_name_default_and_custom_name():
    """register_class_name returns the resolved name and stores it in class_to_name."""
    reg = SchemaRegistry()

    class A: ...

    class B: ...

    # default to class.__name__
    name_a = reg.register_class_name(A)
    assert name_a == "A"
    assert reg.class_to_name[A] == "A"

    # custom override
    name_b = reg.register_class_name(B, "B_v2")
    assert name_b == "B_v2"
    assert reg.class_to_name[B] == "B_v2"


def test_resolve_name_for_string_class_and_errors():
    """resolve_name passes through strings, uses mapping for classes, and errors on other types."""
    reg = SchemaRegistry()

    # strings pass through
    assert reg.resolve_name("User") == "User"

    # class with no mapping -> fallback to __name__
    class Ghost: ...

    assert reg.resolve_name(Ghost) == "Ghost"

    # class with mapping -> use mapped name
    class Owner: ...

    reg.register_class_name(Owner, "OwnerAlias")
    assert reg.resolve_name(Owner) == "OwnerAlias"

    # wrong type
    with pytest.raises(TypeError):
        reg.resolve_name(123)  # neither str nor class


def test_put_component_and_clear_and_snapshot():
    """put_component stores entries, clear wipes both maps, snapshot returns the expected shape."""
    reg = SchemaRegistry()
    reg.put_component("Foo", {"type": "object", "properties": {}})
    reg.register_class_name(str, "StringAlias")  # just to populate class_to_name

    snap = reg.snapshot()
    assert "components" in snap and "schemas" in snap["components"]
    assert snap["components"]["schemas"]["Foo"]["type"] == "object"

    # clear resets both components and class_to_name
    reg.clear()
    assert reg.get_components() == {}
    assert reg.class_to_name == {}


# ------------------------------ Context management ------------------------------


def test_get_set_current_registry_direct_switch():
    """set_current_registry swaps the process-wide current registry used by helpers."""
    original = get_current_registry()
    try:
        reg = SchemaRegistry()
        assert reg is not original
        set_current_registry(reg)
        assert get_current_registry() is reg
    finally:
        # restore original to avoid leaking state to other tests
        set_current_registry(original)


def test_use_registry_context_switch_and_restore_on_exit():
    """use_registry switches current registry inside 'with' and restores on exit."""
    original = get_current_registry()
    reg = SchemaRegistry()
    assert get_current_registry() is original

    with use_registry(reg) as active:
        assert active is reg
        assert get_current_registry() is reg
        # mutations are on the new registry
        reg.put_component("Tmp", {"type": "object", "properties": {}})
        assert "Tmp" in reg.get_components()

    # after exit, it restores the original
    assert get_current_registry() is original
    assert "Tmp" in reg.get_components()  # stays in reg; only the pointer switched back


def test_use_registry_restores_on_exception_too():
    """Even if an exception occurs inside the context, the previous registry is restored."""
    original = get_current_registry()
    reg = SchemaRegistry()
    with pytest.raises(RuntimeError):
        with use_registry(reg):
            assert get_current_registry() is reg
            raise RuntimeError("boom")
    assert get_current_registry() is original


def test_nested_use_registry_and_token_handling():
    """Nested use_registry contexts should restore to the correct outer registry in order."""
    root = get_current_registry()
    a = SchemaRegistry()
    b = SchemaRegistry()

    with use_registry(a):
        assert get_current_registry() is a
        with use_registry(b):
            assert get_current_registry() is b
        # exiting inner restores to 'a'
        assert get_current_registry() is a
    # exiting outer restores to root
    assert get_current_registry() is root
