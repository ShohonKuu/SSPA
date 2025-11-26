```yaml
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
```

```python
from ssap.core.schema.fields import field
from ssap.core.schema.decorator import schema


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
    # Single object via ref(Class)
    address = field(ref=Address, required=True, description="Vendor address")
    # Nullable string (OAS 3.1 union)
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
    # Array of objects via ref(Class)
    items = field(
        type_="array",
        required=True,
        description="Products under this category",
        items=Product,
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
    # Single object via ref(Class)
    featuredProduct = field(
        ref=Product,
        required=True,
        description="Featured product of the catalog",
    )
    # Nullable string example
    notes = field(
        type_=["string", "null"],
        description="Optional notes (nullable)",
    )

```