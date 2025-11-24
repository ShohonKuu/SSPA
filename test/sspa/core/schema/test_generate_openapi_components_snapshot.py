import json
import pytest

from sspa.core.schema.decorator import schema, get_components_registry
from sspa.core.schema.fields import field, get_schema_registry
from sspa.core.schema.registry import get_current_registry


@pytest.fixture(autouse=True)
def _reset_registries():
    """
    Ensure a clean state for both registries before each test.
    - fields registry: class -> component name
    - components registry: name -> schema dict
    """
    setattr(get_schema_registry, "_registry", {})
    get_current_registry().clear()
    yield
    setattr(get_schema_registry, "_registry", {})
    get_current_registry().clear()


def test_build_and_print_components_snapshot():
    """Define models via @schema, then print the combined components.schemas as JSON."""

    @schema
    class Address:
        street = field(type_="string", required=True, description="Street line")
        city = field(type_="string", required=True, description="City name")
        country = field(
            type_="string",
            required=True,
            description="ISO country code",
            enum=["US", "CN", "DE", "FR"],
        )
        postalCode = field(
            type_="string",
            required=True,
            description="Postal/ZIP code",
            format_="postal-code",
        )

    @schema
    class Vendor:
        id = field(type_="integer", required=True, description="Vendor ID")
        name = field(type_="string", required=True, description="Vendor display name")
        address = field(ref=Address, required=True, description="Vendor address")
        supportEmail = field(
            type_=["string", "null"],
            description="Support email or null",
            format_="email",
        )

    @schema
    class Price:
        currency = field(
            type_="string",
            required=True,
            description="ISO currency code",
            enum=["USD", "EUR", "CNY"],
        )
        amount = field(type_="number", required=True, description="Monetary amount")
        discounted = field(
            type_="boolean",
            description="Whether a discount is applied",
            default=False,
        )

    @schema
    class Product:
        sku = field(type_="string", required=True, description="Stock keeping unit")
        title = field(type_="string", required=True, description="Product title")
        tags = field(
            type_="array",
            description="Labels for filtering",
            items={"type": "string"},
        )
        price = field(ref=Price, required=True, description="Product price")
        vendor = field(ref=Vendor, required=True, description="Product vendor")
        rating = field(type_="number", description="Average rating 0–5", example=4.6)
        available = field(
            type_="boolean",
            description="Whether the product is available for sale",
        )

    @schema
    class Category:
        name = field(type_="string", required=True, description="Category name")
        items = field(
            type_="array",
            required=True,
            description="Products under this category",
            items=Product,  # class reference -> $ref
        )

    @schema
    class Catalog:
        version = field(
            type_="string",
            required=True,
            description="Schema version string",
            default="1.0",
        )
        generatedAt = field(
            type_="string",
            required=True,
            description="Generation timestamp",
            format_="date-time",
        )
        categories = field(
            type_="array",
            required=True,
            description="Top-level categories",
            items=Category,
        )
        featuredProduct = field(
            ref=Product,
            required=True,
            description="Featured product of the catalog",
        )
        notes = field(
            type_=["string", "null"],
            description="Optional notes (nullable)",
        )

    # Collect components.schemas
    components = get_components_registry()

    # Basic sanity checks
    assert set(components.keys()) >= {
        "Address",
        "Vendor",
        "Price",
        "Product",
        "Category",
        "Catalog",
    }
    assert components["Catalog"]["properties"]["featuredProduct"] == {
        "$ref": "#/components/schemas/Product"
    }
    assert components["Category"]["properties"]["items"]["items"] == {
        "$ref": "#/components/schemas/Product"
    }

    # Compose a minimal OpenAPI fragment to print
    openapi_fragment = {"components": {"schemas": components}}

    # Pretty-print JSON snapshot (use -s to see it when running pytest)
    print(json.dumps(openapi_fragment, indent=2, sort_keys=True))
