from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Iterable, List, Type

from ssap.core.path.registry import get_current_path_registry
from ssap.tools.exporter import export_split_docs


def _iter_py_files(root: Path) -> Iterable[Path]:
    """
    Yield all Python files under `root` recursively.
    """
    for p in root.rglob("*.py"):
        yield p


def _import_module_from_file(pyfile: Path):
    """
    Import a Python file as a transient module; no package layout required.
    The module key is the posix path to avoid name collisions.
    """
    module_name = f"dsl_{pyfile.stem}_{abs(hash(pyfile.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, pyfile)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _collect_schema_classes(mod) -> List[Type[Any]]:
    """
    Collect classes decorated by @schema (they carry __schema_name__).
    """
    out: List[Type[Any]] = []
    for v in vars(mod).values():
        if isinstance(v, type) and getattr(v, "__schema_name__", None):
            out.append(v)
    return out


def _force_source(obj: Any, new_source: Path) -> None:
    """
    Override recorded source paths so the exporter mirrors the DSL directory
    into the docs/ directory (schema + path share this helper safely).
    """
    pseudo = str(new_source)
    setattr(obj, "__schema_source__", pseudo)
    setattr(obj, "__path_source__", pseudo)


def run_export(
    *,
    dsl_root: Path,
    docs_root: Path,
    title: str,
    version: str,
    verbose: bool = False,
) -> Path:
    """
    High-level pipeline:
      1) Import all modules under dsl/schemas and dsl/paths
      2) Collect @schema classes
      3) Remap recorded sources into docs/ mirror
      4) Call export_split_docs to write:
         - docs/openapi.yaml
         - docs/schemas/**.yaml
         - docs/paths/**.yaml
    Returns:
      Path to docs/openapi.yaml
    """
    schemas_dir = dsl_root / "schemas"
    paths_dir = dsl_root / "paths"

    if not schemas_dir.exists() or not paths_dir.exists():
        raise SystemExit(
            "DSL root must contain both 'schemas/' and 'paths/' directories."
        )

    schema_classes: List[type] = []
    for py in _iter_py_files(schemas_dir):
        mod = _import_module_from_file(py)
        found = _collect_schema_classes(mod)
        if verbose and found:
            print(f"[schema] {py}: {', '.join(c.__name__ for c in found)}")
        schema_classes.extend(found)

    path_classes: List[type] = []
    for py in _iter_py_files(paths_dir):
        mod = _import_module_from_file(py)
        if verbose:
            print(f"[path]   {py}")
        for v in vars(mod).values():
            if isinstance(v, type) and getattr(v, "__path_url__", None):
                try:
                    rel = py.resolve().relative_to(paths_dir.resolve())
                except Exception:
                    rel = Path(f"{v.__name__}.py")
                _force_source(v, docs_root / "paths" / rel)
                path_classes.append(v)

    for cls in schema_classes:
        src = (
            Path(getattr(cls, "__schema_source__", ""))
            if getattr(cls, "__schema_source__", None)
            else None
        )
        try:
            rel = src.resolve().relative_to(schemas_dir.resolve()) if src else None
        except Exception:
            rel = None
        if rel is None:
            rel = Path(f"{cls.__module__.split('.')[-1]}.py")
        _force_source(cls, docs_root / "schemas" / rel)

    reg = get_current_path_registry()
    reg.clear()
    for cls in path_classes:
        reg.add_class(getattr(cls, "__path_url__", ""), cls)

    openapi_path = export_split_docs(
        docs_root=docs_root,
        openapi_info={"title": title, "version": version},
        classes=schema_classes,
    )
    if verbose:
        print(f"[ok] wrote {openapi_path}")
    return openapi_path


def main(argv: List[str] | None = None) -> None:
    """
    CLI entry point.
    """
    ap = argparse.ArgumentParser(
        prog="sspa-export", description="Export split OpenAPI docs from DSL."
    )
    ap.add_argument(
        "--dsl",
        required=True,
        help="Root directory of DSL (must contain 'schemas/' and 'paths/').",
    )
    ap.add_argument("--out", required=True, help="Output docs directory.")
    ap.add_argument("--title", default="API", help="OpenAPI info.title")
    ap.add_argument("--version", default="1.0.0", help="OpenAPI info.version")
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose logs.")
    args = ap.parse_args(argv)

    dsl_root = Path(args.dsl).resolve()
    docs_root = Path(args.out).resolve()

    run_export(
        dsl_root=dsl_root,
        docs_root=docs_root,
        title=args.title,
        version=args.version,
        verbose=args.verbose,
    )
