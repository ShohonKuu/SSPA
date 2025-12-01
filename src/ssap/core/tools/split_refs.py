from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _rel_under(base: Path, file_path: Optional[str]) -> Optional[Path]:
    """
    Return the relative path of file_path under base, or None if it is not under base.
    """
    if not file_path:
        return None
    p = Path(file_path).resolve()
    try:
        return p.relative_to(base.resolve())
    except Exception:
        return None


def schema_target_path(
    docs_root: Path, schema_source: Optional[str], file_id: str
) -> Path:
    """
    Map python file under docs/schemas/**.py to docs/schemas/**/<file_id>.yaml
    """
    rel = _rel_under(docs_root / "schemas", schema_source) or Path(file_id + ".yaml")
    return (docs_root / "schemas" / rel).with_name(file_id + ".yaml")


def path_target_path(docs_root: Path, path_source: Optional[str], file_id: str) -> Path:
    """
    Map python file under docs/paths/**.py to docs/paths/**/<file_id>.yaml
    """
    rel = _rel_under(docs_root / "paths", path_source) or Path(file_id + ".yaml")
    return (docs_root / "paths" / rel).with_name(file_id + ".yaml")


def rel_ref(from_file: Path, to_file: Path) -> str:
    """
    Compute a relative $ref string from one YAML file to another YAML file.
    """
    rel = os.path.relpath(to_file.resolve(), start=from_file.resolve().parent)
    rel = rel.replace("\\", "/")
    if not rel.startswith("."):
        rel = "./" + rel
    return rel
