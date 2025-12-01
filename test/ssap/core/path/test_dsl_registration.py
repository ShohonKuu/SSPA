# Purpose: Ensure @path and method decorators (with full-name param builders)
#          attach metadata correctly and register into a fresh PathRegistry.

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
from ssap.core.path.registry import PathRecord
from ssap.core.path.model import PathItem


@pytest.fixture()
def fresh_registry():
    reg = PathRegistry()
    with use_path_registry(reg):
        yield reg


@pytest.fixture()
def StoreCatalog(fresh_registry):
    @path(
        "store_catalog",
        url="/stores/{storeId}/catalog",
        tags=["Store"],
        params=[
            path_param(
                "storeId",
                "integer",
                fmt="int64",
                required=True,
                desc="Unique store identifier",
            ),
        ],
        summary="Store catalog APIs",
        description="Ops on catalog",
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
                resp(200, json_media({"type": "object"}), desc="Catalog found"),
                resp(304, desc="Not Modified"),
            ],
        )
        def get(self):
            return [{"ok": True}, None]

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


def test_path_class_metadata_attached(StoreCatalog):
    assert getattr(StoreCatalog, "__path_url__") == "/stores/{storeId}/catalog"
    assert getattr(StoreCatalog, "__path_tags__") == ["Store"]
    assert isinstance(getattr(StoreCatalog, "__path_params__"), list)
    assert getattr(StoreCatalog, "__path_summary__") == "Store catalog APIs"
    assert getattr(StoreCatalog, "__path_description__") == "Ops on catalog"


def test_registry_created_for_url(fresh_registry, StoreCatalog):
    assert "/stores/{storeId}/catalog" in fresh_registry.all()
    record = fresh_registry.all()["/stores/{storeId}/catalog"]
    assert isinstance(record, PathRecord)
    assert isinstance(record.item, PathItem)
    assert StoreCatalog in record.classes


def test_method_functions_have_operation_metadata(StoreCatalog):
    for fn_name in ("get", "put", "delete"):
        fn = getattr(StoreCatalog, fn_name)
        assert getattr(fn, "__http_method__") in {"get", "put", "delete"}
        assert isinstance(getattr(fn, "__op_responses__"), list)
        assert isinstance(getattr(fn, "__op_params__"), list)
        if fn_name == "put":
            assert getattr(fn, "__op_request__") is not None
        else:
            assert getattr(fn, "__op_request__") is None


def test_method_return_convention_example_list(StoreCatalog):
    sc = StoreCatalog()
    assert isinstance(sc.get(), list)
    assert isinstance(sc.put(), list)
    assert isinstance(sc.delete(), list)


def test_default_path_file_id_from_url(fresh_registry):
    @path(url="/foo/{id}/bar-baz")
    class Sample:
        pass

    assert getattr(Sample, "__path_file_id__") == "foo_id_bar-baz"
