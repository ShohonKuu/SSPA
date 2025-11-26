import yaml
import difflib

from ssap.core.schema.decorator import schema, get_components_registry
from ssap.core.schema.registry import get_current_registry
from ssap.core.schema.fields import field, get_schema_registry


def setup_function(_fn):
    """Reset registries so the snapshot is deterministic for each test."""
    setattr(get_schema_registry, "_registry", {})
    get_current_registry().clear()


def _canonical_yaml(data: dict) -> str:
    """Dump dict to a canonical YAML string for stable diffs."""
    return yaml.safe_dump(
        data,
        sort_keys=True,  # canonical ordering for stable comparison
        allow_unicode=True,
        default_flow_style=False,
    )


def test_dump_yaml_and_compare_equivalence():
    """Compare generated YAML with expected YAML; on failure show a concise unified diff."""

    # --- Define all @schema classes INSIDE the test (after reset) ---
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

    # --- Build generated YAML (canonicalized) ---
    generated = {"components": {"schemas": get_components_registry()}}
    gen_yaml = _canonical_yaml(generated)

    # --- Expected YAML from spec (canonicalized) ---
    expected_yaml = """
components:
  schemas:
    Address:
      type: object
      properties:
        street:
          type: string
          description: Street line
        city:
          type: string
          description: City name
        country:
          type: string
          description: ISO country code
          enum: ["US", "CN", "DE", "FR"]
        postalCode:
          type: string
          description: Postal/ZIP code
          format: postal-code
      required:
        - street
        - city
        - country
        - postalCode

    Vendor:
      type: object
      properties:
        id:
          type: integer
          description: Vendor ID
        name:
          type: string
          description: Vendor display name
        address:
          $ref: "#/components/schemas/Address"
        supportEmail:
          type: ["string", "null"]
          description: Support email or null
          format: email
      required:
        - id
        - name
        - address

    Price:
      type: object
      properties:
        currency:
          type: string
          description: ISO currency code
          enum: ["USD", "EUR", "CNY"]
        amount:
          type: number
          description: Monetary amount
        discounted:
          type: boolean
          description: Whether a discount is applied
          default: false
      required:
        - currency
        - amount

    Product:
      type: object
      properties:
        sku:
          type: string
          description: Stock keeping unit
        title:
          type: string
          description: Product title
        tags:
          type: array
          description: Labels for filtering
          items:
            type: string
        price:
          $ref: "#/components/schemas/Price"
        vendor:
          $ref: "#/components/schemas/Vendor"
        rating:
          type: number
          description: Average rating 0–5
          example: 4.6
        available:
          type: boolean
          description: Whether the product is available for sale
      required:
        - sku
        - title
        - price
        - vendor

    Category:
      type: object
      properties:
        name:
          type: string
          description: Category name
        items:
          type: array
          description: Products under this category
          items:
            $ref: "#/components/schemas/Product"
      required:
        - name
        - items

    Catalog:
      type: object
      properties:
        version:
          type: string
          description: Schema version string
          default: "1.0"
        generatedAt:
          type: string
          description: Generation timestamp
          format: date-time
        categories:
          type: array
          description: Top-level categories
          items:
            $ref: "#/components/schemas/Category"
        featuredProduct:
          $ref: "#/components/schemas/Product"
        notes:
          type: ["string", "null"]
          description: Optional notes (nullable)
      required:
        - version
        - generatedAt
        - categories
        - featuredProduct
"""
    exp_yaml = _canonical_yaml(yaml.safe_load(expected_yaml))

    # --- Compare; on failure show a concise diff only ---
    if gen_yaml != exp_yaml:
        diff = "\n".join(
            difflib.unified_diff(
                exp_yaml.splitlines(),
                gen_yaml.splitlines(),
                fromfile="expected.yaml",
                tofile="generated.yaml",
                lineterm="",
                n=3,  # three lines of context for brevity
            )
        )
        raise AssertionError(diff)

    assert True  # quiet success
