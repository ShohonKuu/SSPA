# Purpose: End-to-end showcase for split exporters.
# - annotations capture file_id + source
# - split writers create files mirroring python relative dirs
# - openapi.yaml references split files via relative $ref
# - split files rewrite components refs to relative schema files

from pathlib import Path

from ssap.core.schema.decorator import schema
from ssap.core.schema.fields import field
from ssap.core.path import (
    PathRegistry,
    use_path_registry,
    path,
    get,
    path_param,
    resp,
    json_media,
)
from ssap.core.tools.exporter import export_split_docs


def _force_source(obj, pseudo_path: Path):
    """
    Inject a fake __schema_source__/__path_source__ so the exporter
    can map python file location under docs/{schemas,paths}.
    """
    pseudo = str(pseudo_path)
    setattr(obj, "__schema_source__", pseudo)
    setattr(obj, "__path_source__", pseudo)


@schema("MenuItem")
class MenuItem:
    name = field(type_="string", required=True, description="Dish name")
    price = field(type_="number", required=True, description="Dish price")


@schema("Menu")
class Menu:
    items = field(type_="array", required=True, description="Dish list", items=MenuItem)


@path("restaurant_menu", url="/restaurants/{id}/menu", tags=["Restaurant"])
class RestaurantMenuAPI:
    @get(
        summary="Get menu by restaurant id",
        params=[path_param("id", "integer", fmt="int64", required=True, desc="Restaurant id")],
        responses=[
            resp(200, json_media({"$ref": "#/components/schemas/Menu"}), desc="OK"),
            resp(404, desc="Not found"),
        ],
    )
    def get(self):
        return [
            {"items": [{"name": "Fried Rice", "price": 12.5}]},
            None,
        ]


def test_export_split_docs(tmp_path: Path):
    """
    Verify:
      - files are written under docs/{schemas,paths}/... mirroring python relative dirs
      - openapi.yaml references split files via relative $ref
      - split files rewrite component $refs to relative schema files
    """
    docs_root = tmp_path / "docs"
    _force_source(MenuItem, docs_root / "schemas" / "resturant" / "re_a_sc.py")
    _force_source(Menu, docs_root / "schemas" / "resturant" / "re_b_sc.py")
    _force_source(RestaurantMenuAPI, docs_root / "paths" / "resturant" / "re_a_path.py")

    reg = PathRegistry()
    with use_path_registry(reg):
        reg.add_class(RestaurantMenuAPI.__path_url__, RestaurantMenuAPI)
        openapi_path = export_split_docs(
            docs_root=docs_root,
            openapi_info={"title": "Demo API", "version": "1.0.0"},
            classes=[MenuItem, Menu],
        )

    assert openapi_path.exists()
    content = openapi_path.read_text(encoding="utf-8")
    assert "./paths/resturant/restaurant_menu.yaml" in content
    assert "./schemas/resturant/MenuItem.yaml" in content
    assert "./schemas/resturant/Menu.yaml" in content

    menu_item_yaml = docs_root / "schemas" / "resturant" / "MenuItem.yaml"
    menu_yaml = docs_root / "schemas" / "resturant" / "Menu.yaml"
    path_yaml = docs_root / "paths" / "resturant" / "restaurant_menu.yaml"

    assert menu_item_yaml.exists()
    assert menu_yaml.exists()
    assert path_yaml.exists()

    path_text = path_yaml.read_text(encoding="utf-8")
    assert "../../schemas/resturant/Menu.yaml" in path_text

    menu_text = menu_yaml.read_text(encoding="utf-8")
    assert "./MenuItem.yaml" in menu_text
