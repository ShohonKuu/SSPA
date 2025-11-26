from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

HTTPMethod = Literal["get", "put", "post", "delete", "patch", "options", "head"]


@dataclass
class SchemaRef:
    ref: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    def to_schema(self) -> Dict[str, Any]:
        if self.ref:
            return {"$ref": self.ref}
        return dict(self.raw or {})


@dataclass
class MediaType:
    schema: SchemaRef
    examples: Optional[Dict[str, Any]] = None
    example: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {"schema": self.schema.to_schema()}
        if self.example is not None:
            out["example"] = self.example
        if self.examples is not None:
            out["examples"] = self.examples
        return out


@dataclass
class RequestBody:
    required: bool
    description: str = ""
    content: Dict[str, MediaType] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "required": self.required,
            "description": self.description,
            "content": {k: v.to_dict() for k, v in self.content.items()},
        }


@dataclass
class Response:
    description: str
    headers: Optional[Dict[str, Dict[str, Any]]] = None
    content: Optional[Dict[str, MediaType]] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {"description": self.description}
        if self.headers:
            out["headers"] = self.headers
        if self.content:
            out["content"] = {k: v.to_dict() for k, v in self.content.items()}
        return out


@dataclass
class Parameter:
    name: str
    in_: Literal["path", "query", "header", "cookie"]
    required: bool
    schema: Dict[str, Any]
    description: str = ""
    example: Optional[Any] = None
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "in": self.in_,
            "required": self.required,
            "schema": self.schema,
        }
        if self.description:
            d["description"] = self.description
        if self.example is not None:
            d["example"] = self.example
        if self.deprecated:
            d["deprecated"] = True
        return d


@dataclass
class Operation:
    summary: Optional[str] = None
    operationId: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    requestBody: Optional[RequestBody] = None
    responses: Dict[str, Response] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "responses": {k: v.to_dict() for k, v in self.responses.items()}
        }
        if self.summary:
            out["summary"] = self.summary
        if self.operationId:
            out["operationId"] = self.operationId
        if self.description:
            out["description"] = self.description
        if self.tags:
            out["tags"] = self.tags
        if self.parameters:
            out["parameters"] = [p.to_dict() for p in self.parameters]
        if self.requestBody:
            out["requestBody"] = self.requestBody.to_dict()
        return out


@dataclass
class PathItem:
    parameters: List[Parameter] = field(default_factory=list)
    methods: Dict[HTTPMethod, Operation] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.parameters:
            d["parameters"] = [p.to_dict() for p in self.parameters]
        for m, op in self.methods.items():
            d[m] = op.to_dict()
        return d
