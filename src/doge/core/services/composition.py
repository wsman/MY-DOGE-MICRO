"""Deprecated composition root — re-exported from ``doge.application.composition``.

This module previously contained the canonical service factories. In Sprint 007
the composition root moved to ``doge.application.composition`` so that
``doge.core.services`` depends only on ``doge.core.ports`` and contains no
infrastructure imports.

This file is kept as a temporary re-export shim for legacy callers
(``src/cli.py``, ``src/doge/interfaces/api/routers/scan.py``, ``src/micro/industry_analyzer.py``,
etc.) and will be removed in Sprint 008 after those callers are migrated.
"""

import warnings

# Re-export everything from the new canonical composition root.
# The deprecation warning is issued on first import of this module.
warnings.warn(
    "doge.core.services.composition is deprecated; "
    "use doge.application.composition instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.application.composition import (  # noqa: F401
    build_anomaly_service,
    build_breadth_service,
    build_catalog_use_case,
    build_generate_anomaly_report_use_case,
    build_generate_industry_report_use_case,
    build_generate_macro_report_use_case,
    build_generate_market_overview_use_case,
    build_industry_report_use_case,
    build_manage_notes_use_case,
    build_metadata_source,
    build_note_repository,
    build_populate_stock_names_use_case,
    build_query_ticker_use_case,
    build_ranking_service,
    build_report_repository,
    build_scan_market_use_case,
    build_schema_browser,
    build_stock_repository,
    build_stock_service,
    build_view_repository,
    build_view_service,
    refresh_views,
)

__all__ = [
    "build_view_repository",
    "build_view_service",
    "build_stock_repository",
    "build_stock_service",
    "build_report_repository",
    "build_schema_browser",
    "build_note_repository",
    "build_metadata_source",
    "build_ranking_service",
    "build_breadth_service",
    "build_anomaly_service",
    "refresh_views",
    "build_scan_market_use_case",
    "build_generate_macro_report_use_case",
    "build_manage_notes_use_case",
    "build_query_ticker_use_case",
    "build_generate_market_overview_use_case",
    "build_generate_anomaly_report_use_case",
    "build_generate_industry_report_use_case",
    "build_industry_report_use_case",
    "build_catalog_use_case",
    "build_populate_stock_names_use_case",
]
