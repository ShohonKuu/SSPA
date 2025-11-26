```yaml
paths:
  /stores/{storeId}/catalog:
    # Path-level parameters: apply to all methods below
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
      tags: [Store]
      # Method-specific parameters (only for GET)
      parameters:
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
        "304":
          description: Not Modified

    put:
      summary: Replace catalog for the store
      tags: [Store]
      # Method-specific parameters (only for PUT)
      parameters:
        - name: ifMatch
          in: header
          required: false
          description: ETag for optimistic concurrency control
          schema: { type: string }
      requestBody:
        required: true
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
      tags: [Store]
      # Method-specific parameters (only for DELETE)
      parameters:
        - name: reason
          in: query
          required: false
          description: Optional deletion reason
          schema: { type: string }
      responses:
        "204": { description: Deleted }
        "404": { description: Not found }

```

```python

from ssap.http import (
    path, get, put, delete,
    pth, q, hdr, body, resp, json as mt,
    ex, auto_ex,
)
from your.schemas import Catalog  # your @schema class, auto-resolved to $ref


@path(
    "/stores/{storeId}/catalog",
    tags=["Store"],
    params=[
        pth("storeId", "integer", fmt="int64", required=True, desc="Unique store identifier"),
    ],
)
class StoreCatalog:

    @get(
        summary="Get catalog by store ID",
        op_id="getStoreCatalogById",
        params=[
            hdr("ifNoneMatch", "string", required=False, desc="Optional ETag for conditional GET"),
            q("includeDrafts", "boolean", required=False, default=False, desc="Include draft items"),
        ],
        responses=[
            resp(200, mt(Catalog), desc="Catalog found"),
            resp(304, desc="Not Modified"),
        ],
    )
    def get(self):
        # Return values match responses order: [for 200, for 304]
        return [
            auto_ex(Catalog, overrides={"version": "1.0"}),  # example for 200
            None,  # 304 has no body
        ]

    @put(
        summary="Replace catalog for the store",
        op_id="putStoreCatalogById",
        params=[
            hdr("ifMatch", "string", required=False, desc="ETag for optimistic concurrency control"),
        ],
        request=body(
            mt(Catalog),
            required=True,
            desc="Catalog payload",
        ),
        responses=[
            resp(200, desc="Catalog updated"),
            resp(201, desc="Catalog created"),
            resp(409, desc="Conflict (ETag mismatch"))

    ,
    ],
    )

    def put(self):
        # Order: [for 200, for 201, for 409]
        return [
            ex(Catalog, version="1.1"),  # 200 example
            ex(Catalog, version="1.1"),  # 201 example
            None,  # 409 no body
        ]

    @delete(
        summary="Delete store catalog",
        op_id="deleteStoreCatalogById",
        params=[
            q("reason", "string", required=False, desc="Optional deletion reason"),
        ],
        responses=[
            resp(204, desc="Deleted"),
            resp(404, desc="Not found"),
        ],
    )
    def delete(self):
        # Order: [for 204, for 404]
        return [
            None,  # 204 no body
            None,  # 404 no body
        ]

```