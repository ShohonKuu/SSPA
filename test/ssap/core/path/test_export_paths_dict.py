# Purpose: Ensure export_paths_dict() builds an OpenAPI 'paths' dict from DSL metadata
#          and maps method return lists to response examples.

import pytest

from ssap.core.path import (
    PathRegistry,
    use_path_registry,
    path,
    get,
    put,
    delete,
    path_param,
    query_param,
    header_param,
    body,
    resp,
    json_media,
)
from ssap.core.path.export import export_paths_dict


@pytest.fixture()
def fresh_registry():
    reg = PathRegistry()
    with use_path_registry(reg):
        yield reg


@pytest.fixture()
def StoreCatalog(fresh_registry):
    @path(
        "/stores/{storeId}/catalog",
        tags=["Store"],
        params=[
            path_param(
                "storeId",
                "integer",
                fmt="int64",
                required=True,
                desc="Unique store identifier",
            )
        ],
    )
    class _StoreCatalog:

        @get(
            op_id="getStoreCatalogById",
            summary="Get catalog by store ID",
            params=[
                header_param(
                    "ifNoneMatch",
                    "string",
                    required=False,
                    desc="Optional ETag for conditional GET",
                ),
                query_param(
                    "includeDrafts",
                    "boolean",
                    required=False,
                    default=False,
                    desc="Include draft items",
                ),
            ],
            responses=[
                # use a $ref string to avoid depending on schema components here
                resp(
                    200,
                    json_media({"$ref": "#/components/schemas/Catalog"}),
                    desc="Catalog found",
                ),
                resp(304, desc="Not Modified"),
            ],
        )
        def get(self):
            # map to 200 example and 304 none
            return [
                {
                    "version": "1.0",
                    "categories": [],
                },  # example goes into 200/application-json
                None,
            ]

        @put(
            op_id="putStoreCatalogById",
            summary="Replace catalog",
            params=[
                header_param(
                    "ifMatch", "string", required=False, desc="ETag for concurrency"
                )
            ],
            request=body(
                json_media({"$ref": "#/components/schemas/Catalog"}),
                required=True,
                desc="Upsert payload",
            ),
            responses=[
                resp(200, desc="Updated"),
                resp(201, desc="Created"),
                resp(409, desc="Conflict"),
            ],
        )
        def put(self):
            return [None, None, None]

        @delete(
            op_id="deleteStoreCatalogById",
            summary="Delete catalog",
            params=[
                query_param(
                    "reason", "string", required=False, desc="Optional deletion reason"
                )
            ],
            responses=[resp(204, desc="Deleted"), resp(404, desc="Not found")],
        )
        def delete(self):
            return [None, None]

    return _StoreCatalog


def test_export_paths_basic(StoreCatalog):
    paths = export_paths_dict()
    assert "/stores/{storeId}/catalog" in paths

    item = paths["/stores/{storeId}/catalog"]
    assert "get" in item and "responses" in item["get"]
    r200 = item["get"]["responses"]["200"]
    assert r200["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Catalog"
    }
    assert r200["content"]["application/json"]["example"] == {
        "version": "1.0",
        "categories": [],
    }
    assert "content" not in item["get"]["responses"]["304"]

    assert "put" in item and "responses" in item["put"]
    assert item["put"]["responses"]["200"]["description"] == "Updated"

    assert "delete" in item and "responses" in item["delete"]
    assert item["delete"]["responses"]["204"]["description"] == "Deleted"
