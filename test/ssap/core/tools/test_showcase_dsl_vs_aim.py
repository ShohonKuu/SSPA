# ruff: noqa: E402
# Purpose: Compare generated split docs vs AIM (golden YAML).
# - Writes split files to tmp_path/docs
# - Compares openapi.yaml, path yaml, and schema yamls
# - Uses canonical YAML + unified diff on mismatch

from pathlib import Path
import sys
import yaml
import difflib

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from examples.example_showcase.dsl.schemas.resturant.menu import MenuItem, Menu
from examples.example_showcase.dsl.paths.resturant.restaurant_menu import RestaurantMenuAPI
from ssap.core.path import PathRegistry, use_path_registry
from ssap.core.tools.exporter import export_split_docs


def _force_source(obj, pseudo_path: Path):
    """
    Inject a fake __schema_source__/__path_source__ under docs/, so exporter mirrors dirs.
    """
    pseudo = str(pseudo_path)
    setattr(obj, "__schema_source__", pseudo)
    setattr(obj, "__path_source__", pseudo)


def _canonical_yaml_str(text: str) -> str:
    """
    Parse YAML then dump canonically for deterministic comparison.
    """
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


def test_showcase_dsl_vs_aim(tmp_path: Path):
    docs_root = tmp_path / "docs"
    aim_root = ROOT / "examples" / "example_showcase" / "aim"

    _force_source(MenuItem, docs_root / "schemas" / "resturant" / "menu.py")
    _force_source(Menu, docs_root / "schemas" / "resturant" / "menu.py")
    _force_source(RestaurantMenuAPI, docs_root / "paths" / "resturant" / "restaurant_menu.py")

    reg = PathRegistry()
    with use_path_registry(reg):
        reg.add_class(RestaurantMenuAPI.__path_url__, RestaurantMenuAPI)
        openapi_path = export_split_docs(
            docs_root=docs_root,
            openapi_info={"title": "Demo API", "version": "1.0.0"},
            classes=[MenuItem, Menu],
        )

    gen_openapi = openapi_path.read_text(encoding="utf-8")
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
