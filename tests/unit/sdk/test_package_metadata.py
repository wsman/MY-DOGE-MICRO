import json
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[3]


def _toml_load(path: Path):
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
        tomllib = pytest.importorskip("tomli")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_python_sdk_declares_pep517_wheel_build_metadata():
    payload = _toml_load(ROOT / "packages" / "doge-sdk-python" / "pyproject.toml")

    assert payload["build-system"]["build-backend"] == "setuptools.build_meta"
    assert "setuptools>=61.0" in payload["build-system"]["requires"]
    assert "wheel" in payload["build-system"]["requires"]
    assert payload["project"]["name"] == "doge-sdk"
    assert payload["project"]["requires-python"] == ">=3.10"
    assert "httpx>=0.28.0" in payload["project"]["dependencies"]


def test_typescript_sdk_package_exports_dist_only():
    payload = json.loads((ROOT / "packages" / "doge-sdk-typescript" / "package.json").read_text(encoding="utf-8"))

    assert payload["main"] == "dist/index.js"
    assert payload["types"] == "dist/index.d.ts"
    assert payload["exports"]["."]["import"] == "./dist/index.js"
    assert payload["exports"]["."]["types"] == "./dist/index.d.ts"
    assert payload["files"] == ["dist"]
    assert payload["private"] is True


def test_typescript_sdk_uses_node_esm_relative_specifiers():
    src_dir = ROOT / "packages" / "doge-sdk-typescript" / "src"

    for path in [src_dir / "index.ts", src_dir / "client.ts", src_dir / "session.ts", src_dir / "streaming.ts"]:
        text = path.read_text(encoding="utf-8")
        specifiers = re.findall(r"from\s+['\"](\./[^'\"]+)['\"]", text)
        assert specifiers, f"{path} should contain checked relative imports/exports"
        assert all(specifier.endswith(".js") for specifier in specifiers), (
            f"{path} must use .js relative specifiers so packed ESM imports in Node"
        )
