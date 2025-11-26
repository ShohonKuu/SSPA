# Purpose: Validate response/body/media spec constructors with json_media().

from ssap.core.path.dsl import RespSpec, MediaTypeSpec, RequestBodySpec
from ssap.core.path import resp, json_media, body


def test_resp_no_body_fullname():
    r = resp(204, desc="No Content")
    assert isinstance(r, RespSpec)
    assert r.status == 204 and r.media == () and r.desc == "No Content"


def test_resp_with_json_media_and_extra_types_fullname():
    r = resp(
        200, json_media({"type": "object"}), desc="OK", extra_types=["application/xml"]
    )
    assert len(r.media) == 2
    cts = sorted([m.content_type for m in r.media])
    assert cts == ["application/json", "application/xml"]
    assert isinstance(r.media[0], MediaTypeSpec)
    assert r.media[0].schema == {"type": "object"}


def test_request_body_builder_fullname():
    rb = body(
        json_media({"$ref": "#/components/schemas/Catalog"}),
        required=True,
        desc="payload",
    )
    assert isinstance(rb, RequestBodySpec)
    assert rb.required is True and rb.desc == "payload"
    assert rb.media.content_type == "application/json"
