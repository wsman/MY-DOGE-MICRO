"""Application use cases — port-backed workflow orchestration.

These are thin shells for Sprint 007-001. Behaviour is filled in by
S007-002 through S007-006 so the application-layer boundary can be established
and tested first.
"""

from doge.application.use_cases.scan_market import ScanMarketUseCase
from doge.application.use_cases.generate_macro_report import GenerateMacroReportUseCase
from doge.application.use_cases.manage_notes import ManageNotesUseCase
from doge.application.use_cases.query_ticker import QueryTickerUseCase
from doge.application.use_cases.generate_market_overview import GenerateMarketOverviewUseCase
from doge.application.use_cases.generate_anomaly_report import GenerateAnomalyReportUseCase
from doge.application.use_cases.generate_catalog import GenerateCatalogUseCase
from doge.application.use_cases.populate_stock_names import PopulateStockNamesUseCase
from doge.application.use_cases.generate_industry_report import GenerateIndustryReportUseCase

__all__ = [
    "ScanMarketUseCase",
    "GenerateMacroReportUseCase",
    "ManageNotesUseCase",
    "QueryTickerUseCase",
    "GenerateMarketOverviewUseCase",
    "GenerateAnomalyReportUseCase",
    "GenerateCatalogUseCase",
    "PopulateStockNamesUseCase",
    "GenerateIndustryReportUseCase",
]
