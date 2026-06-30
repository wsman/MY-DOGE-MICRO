"""Document and evidence tool facade exports."""

from __future__ import annotations

from doge.application.tools.schemas import descriptors_for_names, schemas_for_names
from doge.products.research.tools import ResearchToolProvider

DOCUMENT_TOOL_NAMES = (
    "lookup_evidence",
    "generate_industry_report",
)


def document_tool_descriptors():
    return descriptors_for_names(DOCUMENT_TOOL_NAMES)


def document_tool_schemas():
    return schemas_for_names(DOCUMENT_TOOL_NAMES)


__all__ = [
    "DOCUMENT_TOOL_NAMES",
    "ResearchToolProvider",
    "document_tool_descriptors",
    "document_tool_schemas",
]
