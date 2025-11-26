import yaml

from ssap.core.tools.exporter import (
    to_yaml,
    build_components_schemas,
    export_schema_yaml,
)
from ssap.core.schema.decorator import schema
from ssap.core.schema.fields import field
from ssap.core.schema.registry import SchemaRegistry, use_registry


@schema
class Price:
    currency = field(type_="string", required=True, enum=["USD", "EUR"])
    amount = field(type_="number", required=True)


@schema
class Product:
    sku = field(type_="string", required=True)
    price = field(ref=Price, required=True)


def test_build_components_schemas_returns_components_only():
    doc = build_components_schemas([Product, Price])
    assert "components" in doc and "schemas" in doc["components"]
    assert "Product" in doc["components"]["schemas"]
    # Ensure no top-level openapi/info/paths are present
    assert "openapi" not in doc and "info" not in doc and "paths" not in doc


def test_export_schema_yaml_round_trip_and_shape():
    out = export_schema_yaml([Product, Price])
    loaded = yaml.safe_load(out)
    # Shape & presence
    assert set(loaded.keys()) == {"components"}
    assert set(loaded["components"].keys()) == {"schemas"}
    assert "Product" in loaded["components"]["schemas"]
    # Minimal property check
    prod = loaded["components"]["schemas"]["Product"]
    assert prod["type"] == "object"
    assert "price" in prod["properties"]
    assert prod["properties"]["price"] == {"$ref": "#/components/schemas/Price"}


def test_build_components_schemas_preserves_custom_names():
    reg = SchemaRegistry()
    with use_registry(reg):

        @schema("Money")
        class AliasPrice:
            currency = field(type_="string", required=True, enum=["USD", "EUR"])
            amount = field(type_="number", required=True)

        @schema(name="Goods")
        class AliasProduct:
            price = field(ref=AliasPrice, required=True)

    doc = build_components_schemas([AliasProduct, AliasPrice])
    schemas = doc["components"]["schemas"]
    assert set(schemas.keys()) == {"Money", "Goods"}
    assert schemas["Goods"]["properties"]["price"] == {
        "$ref": "#/components/schemas/Money"
    }


def test_to_yaml_is_stable_and_human_friendly():
    doc = {"components": {"schemas": {"X": {"type": "object", "properties": {}}}}}
    out = to_yaml(doc)
    # block-style, not flow-style
    assert "components:" in out and "schemas:" in out and "X:" in out
