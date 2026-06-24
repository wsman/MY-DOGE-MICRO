import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tools" / "ci" / "sdk-contract-check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("sdk_contract_check", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sdk_contract_check_passes_current_surfaces():
    module = _load_module()

    assert module.validate() == []


def test_sdk_contract_check_reports_missing_tokens():
    module = _load_module()

    errors = module._missing_tokens("surface", "SDK", ("present", "missing"), "present only")

    assert errors == ["surface: SDK missing token 'missing'"]
