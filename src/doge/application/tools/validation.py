"""Financial validation tool facade exports."""

from __future__ import annotations

from doge.application.tools.schemas import descriptors_for_names, schemas_for_names
from doge.products.research.tools import FundamentalToolProvider, ResearchToolProvider

VALIDATION_TOOL_NAMES = (
    "validate_financial_claims",
    "get_financial_statements",
    "get_company_announcements",
    "calculate_financial_ratios",
    "compare_consensus_estimates",
    "get_industry_classification",
    "screen_compliance_risk",
)


def validation_tool_descriptors():
    return descriptors_for_names(VALIDATION_TOOL_NAMES)


def validation_tool_schemas():
    return schemas_for_names(VALIDATION_TOOL_NAMES)


__all__ = [
    "VALIDATION_TOOL_NAMES",
    "FundamentalToolProvider",
    "ResearchToolProvider",
    "validation_tool_descriptors",
    "validation_tool_schemas",
]
