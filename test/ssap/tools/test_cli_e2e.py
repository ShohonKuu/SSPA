# ruff: noqa: E402
# Purpose: Minimal end-to-end test for the CLI 'sspa-export'.
# - Invokes sspa.tools.cli.main() with the example DSL directory
# - Writes split YAML into tmp_path/docs
# - Compares generated openapi.yaml, path yaml, and schema yamls with AIM (golden) files
# - Uses canonical YAML and a short unified diff on mismatch

from pathlib import Path
import sys
import difflib
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ssap.tools.cli import main as cli_main


def _project_root() -> Path:
    """
    Resolve project root relative to this test file.
    Assuming this file lives at: test/ssap/tools/test_cli_e2e.py
    """
    return ROOT


def _canonical_yaml_str(text: str) -> str:
    """
    Parse YAML then dump canonically (sorted keys, block style) for stable diffs.
    """
    data = yaml.safe_load(text)
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True, default_flow_style=False)


def _assert_yaml_equal(generated_text: str, expected_text: str, label: str):
    """
    Compare canonicalized YAML strings; on mismatch show a small unified diff.
    """
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


def test_cli_e2e_exports_and_matches_aim(tmp_path: Path):
    """
    End-to-end:
      1) Run CLI against examples/example_showcase/dsl
      2) Export to tmp_path/docs
      3) Compare with examples/example_showcase/aim
    """
    root = _project_root()
    dsl_dir = root / "examples" / "example_showcase" / "dsl"
    aim_dir = root / "examples" / "example_showcase" / "aim"
    out_dir = tmp_path / "docs"

    assert dsl_dir.exists(), f"Missing DSL dir: {dsl_dir}"
    assert (aim_dir / "openapi.yaml").exists(), "Missing AIM openapi.yaml"

    cli_main(
        [
            "--dsl",
            str(dsl_dir),
            "--out",
            str(out_dir),
            "--title",
            "Demo API",
            "--version",
            "1.0.0",
        ]
    )

    gen_openapi = (out_dir / "openapi.yaml").read_text(encoding="utf-8")
    exp_openapi = (aim_dir / "openapi.yaml").read_text(encoding="utf-8")
    _assert_yaml_equal(gen_openapi, exp_openapi, "openapi.yaml")

    gen_path_file = out_dir / "paths" / "resturant" / "restaurant_menu.yaml"
    exp_path_file = aim_dir / "paths" / "resturant" / "restaurant_menu.yaml"
    assert gen_path_file.exists(), f"Generated path file missing: {gen_path_file}"
    _assert_yaml_equal(
        gen_path_file.read_text(encoding="utf-8"),
        exp_path_file.read_text(encoding="utf-8"),
        "paths/resturant/restaurant_menu.yaml",
    )

    for name in ("MenuItem", "Menu"):
        gen_schema = out_dir / "schemas" / "resturant" / f"{name}.yaml"
        exp_schema = aim_dir / "schemas" / "resturant" / f"{name}.yaml"
        assert gen_schema.exists(), f"Generated schema file missing: {gen_schema}"
        _assert_yaml_equal(
            gen_schema.read_text(encoding="utf-8"),
            exp_schema.read_text(encoding="utf-8"),
            f"schemas/resturant/{name}.yaml",
        )
