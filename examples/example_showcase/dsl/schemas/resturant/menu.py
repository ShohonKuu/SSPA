from ssap.core.schema.decorator import schema
from ssap.core.schema.fields import field


@schema("MenuItem")
class MenuItem:
    name = field(type_="string", required=True, description="Dish name")
    price = field(type_="number", required=True, description="Dish price")


@schema("Menu")
class Menu:
    items = field(type_="array", required=True, description="Dish list", items=MenuItem)
