from ssap.core.path import path, get, path_param, resp, json_media


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
