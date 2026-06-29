"""Sprint E facade completeness checks."""

from __future__ import annotations

import importlib


FACADE_MODULES = [
    "doge.platform.runtime",
    "doge.platform.evidence",
    "doge.platform.governance",
    "doge.platform.workspace",
    "doge.products.market",
    "doge.products.research",
    "doge.products.portfolio",
    "doge.products.quant",
]


def test_facades_export_importable_symbols() -> None:
    for module_name in FACADE_MODULES:
        module = importlib.import_module(module_name)
        exports = getattr(module, "__all__", ())
        assert exports, f"{module_name} has empty __all__"
        for name in exports:
            assert getattr(module, name) is not None, f"{module_name}.{name} did not import"


def test_governance_facade_does_not_export_workspace_capability_registry() -> None:
    import doge.platform.governance as governance
    from doge.platform.workspace import BuildCapabilityRegistry

    assert "BuildCapabilityRegistry" not in governance.__all__
    assert BuildCapabilityRegistry is not None
