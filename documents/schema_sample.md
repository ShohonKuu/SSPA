```yaml
components:
  schemas:
    BarMenu:
      type: object
      properties:
        barName:
          type: string
          description: Name of the bar
        categories:
          type: array
          description: List of menu categories
          items:
            $ref: "#/components/schemas/Category"
      required:
        - barName
        - categories

    Category:
      type: object
      properties:
        name:
          type: string
          description: Category name (e.g., "Signature Cocktails")
        items:
          type: array
          description: Menu items under this category
          items:
            $ref: "#/components/schemas/MenuItem"
      required:
        - name
        - items

    MenuItem:
      type: object
      properties:
        itemName:
          type: string
          description: Drink name
        price:
          type: number
          description: Price (local currency)
        abv:
          type: number
          description: Alcohol by volume (%)
        isSignature:
          type: boolean
          description: Whether it’s a signature drink
        tags:
          type: array
          description: Tags (e.g., "sweet", "sour", "whisky")
          items:
            type: string
      required:
        - itemName
        - price

```

matching python class

```python
# import schema, field, Ref

@schema
class MenuItem:
    itemName    = field(type_="string",  required=True, description="Drink name")
    price       = field(type_="number",  required=True, description="Price (local currency)")
    abv         = field(type_="number",  required=False, description="Alcohol by volume (%)")
    isSignature = field(type_="boolean", required=False, description="Whether it’s a signature drink")
    tags        = field(type_="array",   required=False,
                        description="Tags (e.g., sweet, sour, whisky)",
                        items={"type": "string"})

@schema
class Category:
    name  = field(type_="string", required=True, description="Category name (e.g., Signature Cocktails)")
    items = field(type_="array",  required=True,
                  description="Menu items under this category",
                  items=Ref("MenuItem"))

@schema
class BarMenu:
    barName    = field(type_="string", required=True, description="Name of the bar")
    categories = field(type_="array",  required=True,
                       description="List of menu categories",
                       items=Ref("Category"))


```