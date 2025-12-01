import difflib
import yaml
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
from ssap.core.tools.exporter import (
    build_paths,
)  # uses export_paths_dict under the hood


def _canonical_yaml(data: dict) -> str:
    """
    Dump dict to a canonical YAML string to make diff stable.
    - sort_keys=True for deterministic ordering
    - block style for readability
    """
    return yaml.safe_dump(
        data,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
    )


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
    )
    class _StoreCatalog:

        @get(
            summary="Get catalog by store ID",
            op_id="getStoreCatalogById",
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
                resp(
                    200,
                    json_media({"$ref": "#/components/schemas/Catalog"}),
                    desc="Catalog found",
                ),
                resp(304, desc="Not Modified"),
            ],
        )
        def get(self):
            # examples list matches responses order
            return [
                {"version": "1.0", "categories": []},
                None,
            ]

        @put(
            summary="Replace catalog for the store",
            op_id="putStoreCatalogById",
            params=[
                header_param(
                    "ifMatch",
                    "string",
                    required=False,
                    desc="ETag for optimistic concurrency control",
                ),
            ],
            request=body(
                json_media({"$ref": "#/components/schemas/Catalog"}),
                required=True,
                desc="Catalog payload",
            ),
            responses=[
                resp(200, desc="Catalog updated"),
                resp(201, desc="Catalog created"),
                resp(409, desc="Conflict (ETag mismatch)"),
            ],
        )
        def put(self):
            return [None, None, None]

        @delete(
            summary="Delete store catalog",
            op_id="deleteStoreCatalogById",
            params=[
                query_param(
                    "reason", "string", required=False, desc="Optional deletion reason"
                ),
            ],
            responses=[
                resp(204, desc="Deleted"),
                resp(404, desc="Not found"),
            ],
        )
        def delete(self):
            return [None, None]

    return _StoreCatalog


def test_dump_paths_yaml_and_compare_equivalence(StoreCatalog):
    # Generate
    generated = build_paths()
    gen_yaml = _canonical_yaml(generated)

    # Expected (structurally equivalent; ordering normalized by _canonical_yaml)
    expected_yaml = """
paths:
  /stores/{storeId}/catalog:
    parameters:
      - name: storeId
        in: path
        required: true
        description: Unique store identifier
        schema:
          type: integer
          format: int64
    get:
      summary: Get catalog by store ID
      operationId: getStoreCatalogById
      tags: ["Store"]
      parameters:
        - name: storeId
          in: path
          required: true
          description: Unique store identifier
          schema: { type: integer, format: int64 }
        - name: ifNoneMatch
          in: header
          required: false
          description: Optional ETag for conditional GET
          schema: { type: string }
        - name: includeDrafts
          in: query
          required: false
          description: Include draft items
          schema: { type: boolean, default: false }
      responses:
        "200":
          description: Catalog found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Catalog"
              example:
                version: "1.0"
                categories: []
        "304":
          description: Not Modified
    put:
      summary: Replace catalog for the store
      operationId: putStoreCatalogById
      tags: ["Store"]
      parameters:
        - name: storeId
          in: path
          required: true
          description: Unique store identifier
          schema: { type: integer, format: int64 }
        - name: ifMatch
          in: header
          required: false
          description: ETag for optimistic concurrency control
          schema: { type: string }
      requestBody:
        required: true
        description: Catalog payload
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/Catalog"
      responses:
        "200": { description: Catalog updated }
        "201": { description: Catalog created }
        "409": { description: Conflict (ETag mismatch) }
    delete:
      summary: Delete store catalog
      operationId: deleteStoreCatalogById
      tags: ["Store"]
      parameters:
        - name: storeId
          in: path
          required: true
          description: Unique store identifier
          schema: { type: integer, format: int64 }
        - name: reason
          in: query
          required: false
          description: Optional deletion reason
          schema: { type: string }
      responses:
        "204": { description: Deleted }
        "404": { description: Not found }
"""
    exp_yaml = _canonical_yaml(yaml.safe_load(expected_yaml))

    if gen_yaml != exp_yaml:
        diff = "\n".join(
            difflib.unified_diff(
                exp_yaml.splitlines(),
                gen_yaml.splitlines(),
                fromfile="expected.yaml",
                tofile="generated.yaml",
                lineterm="",
                n=1,
            )
        )
        raise AssertionError(diff)

    assert True
