# Purpose: Validate full-name ParamSpec builders produce correct spec objects.

from ssap.core.path.dsl import ParamSpec
from ssap.core.path import path_param, query_param, header_param, cookie_param


def test_path_param_builder():
    p = path_param("storeId", "integer", fmt="int64", required=True, desc="id")
    assert isinstance(p, ParamSpec)
    assert (p.name, p.in_, p.typ, p.fmt, p.required, p.desc) == (
        "storeId",
        "path",
        "integer",
        "int64",
        True,
        "id",
    )


def test_query_param_builder_with_default_and_example():
    p = query_param(
        "limit", "integer", required=False, desc="max items", default=20, example=10
    )
    assert (p.in_, p.name, p.default, p.example) == ("query", "limit", 20, 10)


def test_header_param_builder_optional():
    p = header_param("ifMatch", "string", required=False, desc="ETag")
    assert (p.in_, p.name, p.required) == ("header", "ifMatch", False)


def test_cookie_param_builder():
    p = cookie_param("session", "string", required=False, desc="Session cookie")
    assert (p.in_, p.name, p.typ, p.required) == ("cookie", "session", "string", False)
