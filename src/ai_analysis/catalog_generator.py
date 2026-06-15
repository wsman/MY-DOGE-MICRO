"""Deprecated catalog-generator module — forwards to ``GenerateCatalogUseCase``.

``src/ai_analysis/catalog_generator.py`` is kept as a backwards-compatible shim
for Sprint 007. The canonical implementation now lives in
``doge.application.use_cases.generate_catalog``. This module re-exports
``generate_catalog()`` so existing scripts and tests keep working. It will be
removed in Sprint 008.
"""
import warnings

warnings.warn(
    "ai_analysis.catalog_generator is deprecated; use "
    "doge.application.use_cases.generate_catalog instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.application.composition import build_catalog_use_case
from doge.application.contracts.request import GenerateCatalogRequest


def generate_catalog():
    """生成完整数据字典"""
    uc = build_catalog_use_case()
    resp = uc.execute(GenerateCatalogRequest())
    print("catalog.json written to {}".format(resp.path))
    return resp


if __name__ == "__main__":
    generate_catalog()
