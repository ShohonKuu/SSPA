# Purpose: Verify that @schema and @path capture file_id and source file path.

from ssap.core.schema.decorator import schema
from ssap.core.schema.fields import field
from ssap.core.path import path, get


@schema("MenuItem")
class MenuItem:
    name = field(type_="string", required=True)


@path("restaurant_menu", url="/restaurants/{id}/menu")
class RestaurantMenu:
    @get(responses=[])
    def get(self):
        return []


def test_schema_annotations_capture():
    assert MenuItem.__schema_file_id__ == "MenuItem"
    assert hasattr(MenuItem, "__schema_source__")


def test_path_annotations_capture():
    assert RestaurantMenu.__path_file_id__ == "restaurant_menu"
    assert RestaurantMenu.__path_url__ == "/restaurants/{id}/menu"
    assert hasattr(RestaurantMenu, "__path_source__")
