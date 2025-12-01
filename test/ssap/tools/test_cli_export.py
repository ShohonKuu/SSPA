# ruff: noqa: E402
# Purpose: smoke test the CLI entry point against the showcase DSL/AIM.

from pathlib import Path
import sys
import yaml
import difflib

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ssap.core.path.registry import PathRegistry, use_path_registry
from ssap.tools.cli import main


def _canonical_yaml_str(text: str) -> str:
    data = yaml.safe_load(text)
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True, default_flow_style=False)


def _assert_yaml_equal(generated_text: str, expected_text: str, label=""):
    gen = _canonical_yaml_str(generated_text)
    exp = _canonical_yaml_str(expected_text)
    if gen != exp:
        diff = "\n".join(
            difflib.unified_diff(
                exp.splitlines(),
                gen.splitlines(),
                fromfile=f"expected:{label}",
                tofile=f"generated:{label}",
                lineterm="",
                n=3,
            )
        )
        raise AssertionError(diff)


def test_cli_export_against_showcase(tmp_path: Path):
    docs_root = tmp_path / "docs"
    dsl_root = ROOT / "examples" / "example_showcase" / "dsl"
    aim_root = ROOT / "examples" / "example_showcase" / "aim"

    with use_path_registry(PathRegistry()):
        main(
            [
                "--dsl",
                str(dsl_root),
                "--out",
                str(docs_root),
                "--title",
                "Demo API",
                "--version",
                "1.0.0",
            ]
        )

    gen_openapi = (docs_root / "openapi.yaml").read_text(encoding="utf-8")
    exp_openapi = (aim_root / "openapi.yaml").read_text(encoding="utf-8")
    _assert_yaml_equal(gen_openapi, exp_openapi, "openapi.yaml")

    gen_path = (docs_root / "paths" / "resturant" / "restaurant_menu.yaml").read_text(
        encoding="utf-8"
    )
    exp_path = (
        aim_root / "paths" / "resturant" / "restaurant_menu.yaml"
    ).read_text(encoding="utf-8")
    _assert_yaml_equal(gen_path, exp_path, "paths/resturant/restaurant_menu.yaml")

    for name in ("MenuItem", "Menu"):
        gen_schema = (docs_root / "schemas" / "resturant" / f"{name}.yaml").read_text(
            encoding="utf-8"
        )
        exp_schema = (
            aim_root / "schemas" / "resturant" / f"{name}.yaml"
        ).read_text(encoding="utf-8")
        _assert_yaml_equal(gen_schema, exp_schema, f"schemas/resturant/{name}.yaml")
