from __future__ import annotations
from typing import Any, Dict, List, Tuple, Type

from .registry import get_current_path_registry
from .model import (
    PathItem,
    Operation,
    Response,
    RequestBody,
    MediaType,
    Parameter,
    SchemaRef,
)
from .dsl import ParamSpec, RequestBodySpec, RespSpec


# ---------- helpers: schema ref & params ----------


def _to_schema_ref(schema_or_class_or_dict: Any) -> SchemaRef:
    # dict: allow inline, including {"$ref": "..."}
    if isinstance(schema_or_class_or_dict, dict):
        if "$ref" in schema_or_class_or_dict:
            return SchemaRef(ref=schema_or_class_or_dict["$ref"])
        return SchemaRef(raw=schema_or_class_or_dict)
    # class: turn into $ref by class/alias name; defer to __schema_name__ or __name__
    if isinstance(schema_or_class_or_dict, type):
        name = getattr(
            schema_or_class_or_dict, "__schema_name__", schema_or_class_or_dict.__name__
        )
        return SchemaRef(ref=f"#/components/schemas/{name}")
    # string: assume it's a $ref path already
    if isinstance(schema_or_class_or_dict, str):
        return SchemaRef(ref=schema_or_class_or_dict)
    # fallback
    return SchemaRef(raw={"type": "object"})


def _param_to_model(p: ParamSpec) -> Parameter:
    schema: Dict[str, Any] = {"type": p.typ}
    if p.fmt:
        schema["format"] = p.fmt
    if p.default is not None:
        schema["default"] = p.default
    return Parameter(
        name=p.name,
        in_=p.in_,
        required=bool(p.required),
        schema=schema,
        description=p.desc or "",
        example=p.example,
    )


def _request_to_model(rb: RequestBodySpec | None) -> RequestBody | None:
    if rb is None:
        return None
    mt = MediaType(schema=_to_schema_ref(rb.media.schema))
    return RequestBody(
        required=rb.required,
        description=rb.desc or "",
        content={rb.media.content_type: mt},
    )


def _response_to_model(r: RespSpec) -> Response:
    if not r.media:
        return Response(description=r.desc or "")
    content = {}
    for m in r.media:
        content[m.content_type] = MediaType(schema=_to_schema_ref(m.schema))
    return Response(description=r.desc or "", content=content)


# ---------- build Operations from a class ----------


def _collect_operations_from_class(
    cls: Type,
) -> List[Tuple[str, Operation, List[RespSpec]]]:
    """
    Scan a @path-decorated class and collect methods decorated by @get/@put/... .
    Returns a list of (method_name, Operation, resp_specs) to be attached to PathItem.
    """
    ops: List[Tuple[str, Operation, List[RespSpec]]] = []
    for attr_name in dir(cls):
        fn = getattr(cls, attr_name)
        method = getattr(fn, "__http_method__", None)
        if not method:
            continue
        cls_tags = list(getattr(cls, "__path_tags__", []) or [])
        op = Operation(
            summary=getattr(fn, "__op_summary__", None),
            operationId=getattr(fn, "__op_id__", None),
            description=getattr(fn, "__op_description__", None),
            tags=cls_tags,
        )
        path_params: List[ParamSpec] = getattr(cls, "__path_params__", []) or []
        method_params: List[ParamSpec] = getattr(fn, "__op_params__", []) or []
        merged: List[Parameter] = []
        for p in path_params + method_params:
            merged.append(_param_to_model(p))
        if merged:
            op.parameters = merged
        op.requestBody = _request_to_model(getattr(fn, "__op_request__", None))
        resp_specs: List[RespSpec] = getattr(fn, "__op_responses__", []) or []
        for rs in resp_specs:
            op.responses[str(rs.status)] = _response_to_model(rs)
        ops.append((method, op, resp_specs))
    return ops


# ---------- map return-list examples -> responses ----------


def _apply_examples(op: Operation, resp_specs: List[RespSpec], ret: List[Any]) -> None:
    """
    Map the returned list onto responses in order.
    - If response has no content: corresponding ret[i] must be None (silently ignore otherwise).
    - If response has one content-type: put ret[i] into its 'example'.
    - If response has multiple content-types: ret[i] must be a dict keyed by content-type.
    """
    if not isinstance(ret, list):
        return

    statuses = list(op.responses.keys())
    for i, val in enumerate(ret):
        if i >= len(statuses):
            break
        resp = op.responses[statuses[i]]
        if not resp.content:
            continue
        if len(resp.content) == 1:
            ct = next(iter(resp.content.keys()))
            resp.content[ct].example = val
        else:
            if isinstance(val, dict):
                for ct, media in resp.content.items():
                    if ct in val:
                        media.example = val[ct]


# ---------- public: build paths dict ----------


def export_paths_dict() -> Dict[str, Any]:
    """
    Assemble OpenAPI 'paths' from the current PathRegistry and attached classes.
    - Does not validate strictly (keeps logic minimal as requested).
    - Attaches examples by calling the instance methods and mapping return-list.
    """
    reg = get_current_path_registry()
    out: Dict[str, Any] = {}
    for url, record in reg.all().items():
        item = PathItem()
        if record.classes:
            first_cls = record.classes[0]
            path_params = getattr(first_cls, "__path_params__", []) or []
            if path_params:
                item.parameters = [_param_to_model(p) for p in path_params]
        for cls in record.classes:
            for method, op, resp_specs in _collect_operations_from_class(cls):
                try:
                    inst = cls()
                    ret = getattr(inst, method)()
                except Exception:
                    ret = None
                if isinstance(ret, list):
                    _apply_examples(op, resp_specs, ret)
                item.methods[method] = op
        out[url] = item.to_dict()
    return out
