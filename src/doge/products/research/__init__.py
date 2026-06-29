"""Research facade."""

from doge.application.use_cases.generate_industry_report import GenerateIndustryReportUseCase
from doge.application.use_cases.generate_macro_report import GenerateMacroReportUseCase
from doge.application.use_cases.industry_analyzer import IndustryAnalyzerAgentUseCase
from doge.application.use_cases.macro_strategist import MacroStrategistAgentUseCase
from doge.application.use_cases.manage_notes import ManageNotesUseCase
from doge.core.ports.financial_connectors import (
    ICompanyAnnouncementRepository,
    IConsensusEstimateRepository,
    IFinancialStatementRepository,
    IIndustryClassificationSource,
)
from doge.core.ports.repository import INoteRepository, IReportRepository
from .tools import FundamentalToolProvider, ResearchToolProvider

__all__ = [
    "FundamentalToolProvider",
    "GenerateIndustryReportUseCase",
    "GenerateMacroReportUseCase",
    "ICompanyAnnouncementRepository",
    "IConsensusEstimateRepository",
    "IFinancialStatementRepository",
    "IIndustryClassificationSource",
    "INoteRepository",
    "IReportRepository",
    "IndustryAnalyzerAgentUseCase",
    "MacroStrategistAgentUseCase",
    "ManageNotesUseCase",
    "ResearchToolProvider",
]
