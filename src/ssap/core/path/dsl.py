from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from .registry import get_current_path_registry


# -------- Param builders (spec-only, converted later) --------
@dataclass(frozen=True)
class ParamSpec:
    name: str
    in_: str
    typ: str
    fmt: Optional[str] = None
    required: Optional[bool] = None
    desc: str = ""
    default: Any = None
    example: Any = None


def path_param(
    name: str,
    typ: str,
    *,
    fmt: str | None = None,
    required: bool = True,
    desc: str = "",
    default=None,
    example=None,
) -> ParamSpec:
    """Full-name helper for path parameters; alias pth kept for backward compatibility."""
    return ParamSpec(
        name=name,
        in_="path",
        typ=typ,
        fmt=fmt,
        required=required,
        desc=desc,
        default=default,
        example=example,
    )


def query_param(
    name: str,
    typ: str,
    *,
    fmt: str | None = None,
    required: bool = False,
    desc: str = "",
    default=None,
    example=None,
) -> ParamSpec:
    """Full-name helper for query parameters; alias q kept for backward compatibility."""
    return ParamSpec(
        name=name,
        in_="query",
        typ=typ,
        fmt=fmt,
        required=required,
        desc=desc,
        default=default,
        example=example,
    )


def header_param(
    name: str,
    typ: str,
    *,
    fmt: str | None = None,
    required: bool = False,
    desc: str = "",
    default=None,
    example=None,
) -> ParamSpec:
    """Full-name helper for header parameters; alias hdr kept for backward compatibility."""
    return ParamSpec(
        name=name,
        in_="header",
        typ=typ,
        fmt=fmt,
        required=required,
        desc=desc,
        default=default,
        example=example,
    )


def cookie_param(name: str, typ: str, **kw):
    return ParamSpec(name=name, in_="cookie", typ=typ, **kw)


# -------- Media / Response / Request spec wrappers --------
@dataclass(frozen=True)
class MediaTypeSpec:
    schema: Any  # class or dict or "$ref string"
    content_type: str = "application/json"


def json_media(schema_or_class: Any) -> MediaTypeSpec:
    """Full-name helper for JSON media; aliases json/mt kept for backward compatibility."""
    return MediaTypeSpec(schema=schema_or_class, content_type="application/json")


json = json_media
mt = json_media


@dataclass(frozen=True)
class RespSpec:
    status: int
    media: tuple[MediaTypeSpec, ...] = ()
    desc: str = ""


def response_spec(
    status: int,
    media: MediaTypeSpec | None = None,
    *,
    desc: str = "",
    extra_types: List[str] | None = None,
) -> RespSpec:
    """Full-name helper for responses; alias resp kept for backward compatibility."""
    if media is None:
        return RespSpec(status=status, media=(), desc=desc)
    medias = [media]
    if extra_types:
        for ct in extra_types:
            medias.append(MediaTypeSpec(schema=media.schema, content_type=ct))
    return RespSpec(status=status, media=tuple(medias), desc=desc)


# Backward compatible alias
resp = response_spec


@dataclass(frozen=True)
class RequestBodySpec:
    media: MediaTypeSpec
    required: bool = False
    desc: str = ""


def request_body(
    media: MediaTypeSpec, *, required: bool = False, desc: str = ""
) -> RequestBodySpec:
    """Full-name helper for request bodies; alias body kept for backward compatibility."""
    return RequestBodySpec(media=media, required=required, desc=desc)


# Backward compatible alias
body = request_body


# -------- Class decorator for path --------
def path(
    url: str,
    *,
    tags: List[str] | None = None,
    params: List[ParamSpec] | None = None,
    summary: str | None = None,
    description: str | None = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
):
    def _wrap(cls: Type) -> Type:
        setattr(cls, "__path_url__", url)
        setattr(cls, "__path_tags__", tags or [])
        setattr(cls, "__path_params__", params or [])
        setattr(cls, "__path_summary__", summary)
        setattr(cls, "__path_description__", description)
        setattr(cls, "__path_security__", security)
        reg = get_current_path_registry()
        reg.ensure(url)
        reg.add_class(url, cls)
        return cls

    return _wrap


# -------- Method decorators (store metadata on functions) --------
def _op(
    method: str,
    *,
    summary: str | None = None,
    op_id: str | None = None,
    description: str | None = None,
    params: List[ParamSpec] | None = None,
    request: RequestBodySpec | None = None,
    responses: List[RespSpec] = [],
):
    def _wrap(func: Callable) -> Callable:
        setattr(func, "__http_method__", method)
        setattr(func, "__op_summary__", summary)
        setattr(func, "__op_id__", op_id)
        setattr(func, "__op_description__", description)
        setattr(func, "__op_params__", params or [])
        setattr(func, "__op_request__", request)
        setattr(func, "__op_responses__", responses)
        return func

    return _wrap


def get(**kwargs):
    return _op("get", **kwargs)


def put(**kwargs):
    return _op("put", **kwargs)


def post(**kwargs):
    return _op("post", **kwargs)


def delete(**kwargs):
    return _op("delete", **kwargs)
