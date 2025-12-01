from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Type

import yaml

from ssap.core.path.export import export_paths_dict
from ssap.core.path.registry import get_current_path_registry
from ssap.core.schema.decorator import get_components_registry, schema
from ssap.core.schema.registry import SchemaRegistry, use_registry
from ssap.core.tools.split_refs import path_target_path, rel_ref, schema_target_path


def to_yaml(data: Dict[str, Any]) -> str:
    """
    Convert a Python dict to a human-friendly YAML string.

    - Uses safe_dump to avoid arbitrary Python tags.
    - Keeps insertion order for readability.
    - Block style for better diffs/reviews.
    """
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


def _ensure_registered(cls: Type, reg: SchemaRegistry) -> None:
    """
    Ensure `cls` has been registered into `reg` as a component schema.
    If not, decorate it with @schema(registry=reg).
    Safe to call multiple times.
    """
    # Fast path: if a class already has a __schema_name__ that exists in reg, skip.
    comp_name = getattr(cls, "__schema_name__", None) or cls.__name__
    if comp_name in reg.get_components():
        return

    # Preserve caller-provided file metadata if present.
    existing_file_id = getattr(cls, "__schema_file_id__", None)
    existing_source = getattr(cls, "__schema_source__", None)

    # Decorate into target registry, preserving any custom component name.
    schema(name=comp_name, registry=reg)(cls)

    if existing_file_id is not None:
        setattr(cls, "__schema_file_id__", existing_file_id)
    if existing_source is not None:
        setattr(cls, "__schema_source__", existing_source)


def build_components_schemas(
    classes: Sequence[Type],
    *,
    registry: Optional[SchemaRegistry] = None,
) -> Dict[str, Any]:
    """
    Build a dict of the form:
      { "components": { "schemas": { <Name>: <Schema>, ... } } }

    - Registers all provided classes into a fresh or given registry.
    - Does NOT include 'openapi', 'info', or 'paths'. This is intentionally
      schema-only for large projects where schemas and paths are managed separately.
    """
    reg = registry or SchemaRegistry()
    with use_registry(reg):
        for cls in classes:
            _ensure_registered(cls, reg)
        return {"components": {"schemas": get_components_registry()}}


def export_schema_yaml(
    classes: Sequence[Type],
    *,
    registry: Optional[SchemaRegistry] = None,
) -> str:
    """
    Convenience one-shot that returns a YAML string for:
      components:
        schemas:
          ...
    """
    doc = build_components_schemas(classes, registry=registry)
    return to_yaml(doc)


def build_openapi_document(
    *,
    info: Dict[str, Any],
    openapi: str = "3.0.1",
    schema_classes: Sequence[Type] | None = None,
    registry: Optional[SchemaRegistry] = None,
) -> Dict[str, Any]:
    """
    Assemble a full OpenAPI document by stitching together paths (from the path DSL)
    and optional schema components.
    """
    doc: Dict[str, Any] = {
        "openapi": openapi,
        "info": info,
        "paths": export_paths_dict(),
    }
    if schema_classes:
        doc.update(build_components_schemas(schema_classes, registry=registry))
    return doc


def export_openapi_yaml(
    *,
    info: Dict[str, Any],
    openapi: str = "3.0.1",
    schema_classes: Sequence[Type] | None = None,
    registry: Optional[SchemaRegistry] = None,
) -> str:
    """
    Convenience helper to dump the full OpenAPI document (paths + components) to YAML.
    """
    return to_yaml(
        build_openapi_document(
            info=info,
            openapi=openapi,
            schema_classes=schema_classes,
            registry=registry,
        )
    )


def build_paths() -> Dict[str, Any]:
    """
    Build a dict of the form:
      { "paths": { <url>: <PathItemDict>, ... } }
    """
    return {"paths": export_paths_dict()}


def export_paths_yaml() -> str:
    """
    Convenience: YAML string for just the paths tree:
      paths:
        /...: ...
    """
    return to_yaml(build_paths())


# -------- helpers: rewrite {"$ref":"#/components/schemas/Name"} -> relative file --------


def _walk_rewrite(
    obj: Any, this_yaml_path: Path, name_to_target: Dict[str, Path]
) -> Any:
    """
    Recursively walk an object and rewrite $ref that point to components/schemas/Name
    into relative file refs like "./Name.yaml" or "../../schemas/.../Name.yaml".
    Non-matching refs are left untouched.
    """
    if isinstance(obj, dict):
        if "$ref" in obj and isinstance(obj["$ref"], str):
            ref = obj["$ref"]
            if ref.startswith("#/components/schemas/"):
                name = ref.split("/")[-1]
                target = name_to_target.get(name)
                if target is not None:
                    obj = dict(obj)
                    obj["$ref"] = rel_ref(this_yaml_path, target)
                    return obj
        out = {}
        for k, v in obj.items():
            out[k] = _walk_rewrite(v, this_yaml_path, name_to_target)
        return out
    if isinstance(obj, list):
        return [_walk_rewrite(x, this_yaml_path, name_to_target) for x in obj]
    return obj


# -------- schemas: split without writing, return path->schema --------


def export_schemas_split_map(
    classes: Iterable[type],
    *,
    docs_root: str | Path,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Path]]:
    """
    Build schemas and return:
      - files: { "<abs target yaml path>": <schema object with local refs> }
      - name_to_target: { "ComponentName": <abs Path to yaml> }
    """
    reg = SchemaRegistry()
    files: Dict[str, Dict[str, Any]] = {}
    name_to_target: Dict[str, Path] = {}

    with use_registry(reg):
        for cls in classes:
            _ensure_registered(cls, reg)

        docs_root = Path(docs_root)
        for name, schema_obj in get_components_registry().items():
            cls = next(
                (
                    c
                    for c in classes
                    if getattr(c, "__schema_name__", c.__name__) == name
                ),
                None,
            )
            file_id = getattr(cls, "__schema_file_id__", name) if cls else name
            src = getattr(cls, "__schema_source__", None) if cls else None
            target = schema_target_path(docs_root, src, file_id)
            name_to_target[name] = target

        for name, target in name_to_target.items():
            schema_obj = get_components_registry()[name]
            rewritten = _walk_rewrite(copy.deepcopy(schema_obj), target, name_to_target)
            files[str(target)] = rewritten

    return files, name_to_target


# -------- paths: split without writing, return (url, file)->pathItem --------


def export_paths_split_list(
    *,
    docs_root: str | Path,
    name_to_target: Dict[str, Path],
) -> List[Tuple[str, str, Dict[str, Any]]]:
    """
    Build paths dict and return list of tuples:
      (url, "<abs target yaml path>", <pathItem object with local schema $refs>)
    """
    paths = export_paths_dict()
    reg = get_current_path_registry()
    out: List[Tuple[str, str, Dict[str, Any]]] = []

    docs_root = Path(docs_root)

    for url, record in reg.all().items():
        if not record.classes:
            continue
        cls = record.classes[0]
        file_id = getattr(cls, "__path_file_id__", "path_item")
        src = getattr(cls, "__path_source__", None)
        target = path_target_path(docs_root, src, file_id)

        path_item_obj = paths[url]
        rewritten = _walk_rewrite(copy.deepcopy(path_item_obj), target, name_to_target)
        out.append((url, str(target), rewritten))

    return out


# -------- write docs tree + openapi index with $refs --------


def write_docs_tree(
    *,
    docs_root: str | Path,
    openapi_info: Dict[str, Any],
    schemas_files: Dict[str, Dict[str, Any]],
    paths_list: List[Tuple[str, str, Dict[str, Any]]],
) -> Path:
    """
    Write:
      docs_root/openapi.yaml
      docs_root/schemas/**.yaml
      docs_root/paths/**.yaml

    And build openapi.yaml with relative $refs:
      paths:
        <url>: { $ref: <relative to openapi.yaml> }
      components:
        schemas:
          <Name>: { $ref: <relative to openapi.yaml> }
    """
    docs_root = Path(docs_root)
    docs_root.mkdir(parents=True, exist_ok=True)

    for p, obj in schemas_files.items():
        path = Path(p)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(to_yaml(obj), encoding="utf-8")
    for _, p, obj in paths_list:
        path = Path(p)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(to_yaml(obj), encoding="utf-8")

    paths_index: Dict[str, Any] = {}
    for url, p, _ in paths_list:
        rel = rel_ref(docs_root / "openapi.yaml", Path(p))
        paths_index[url] = {"$ref": rel}

    components_index: Dict[str, Any] = {}
    for p in schemas_files.keys():
        target = Path(p)
        name = target.stem
        rel = rel_ref(docs_root / "openapi.yaml", target)
        components_index[name] = {"$ref": rel}

    index = {
        "openapi": "3.0.1",
        "info": dict(openapi_info),
        "paths": paths_index,
        "components": {"schemas": components_index},
    }
    (docs_root / "openapi.yaml").write_text(to_yaml(index), encoding="utf-8")
    return docs_root / "openapi.yaml"


# -------- one-shot convenience --------


def export_split_docs(
    *,
    docs_root: str | Path,
    openapi_info: Dict[str, Any],
    classes: Iterable[type],
) -> Path:
    """
    High-level pipeline:
      1) build schemas and compute name->file map
      2) build paths with $ref rewritten to schema files
      3) write tree and openapi.yaml
      4) return openapi.yaml path
    """
    schemas_files, name_to_target = export_schemas_split_map(
        classes, docs_root=docs_root
    )
    paths_list = export_paths_split_list(
        docs_root=docs_root, name_to_target=name_to_target
    )
    return write_docs_tree(
        docs_root=docs_root,
        openapi_info=openapi_info,
        schemas_files=schemas_files,
        paths_list=paths_list,
    )
