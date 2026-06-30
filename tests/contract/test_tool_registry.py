"""Contract tests for canonical tool registry module boundaries."""

from __future__ import annotations

from doge.application.tools import approval, documents, market, portfolio, schemas, validation
from doge.application.tools.factory import build_default_tool_registry
from doge.core.domain.tool_policy import ToolCategory


def _schema_names(items: list[dict]) -> set[str]:
    return {item["function"]["name"] for item in items}


def test_tool_schema_facades_are_backed_by_default_registry() -> None:
    registry_names = _schema_names(build_default_tool_registry().schemas)

    facade_names = set().union(
        _schema_names(market.market_tool_schemas()),
        _schema_names(portfolio.portfolio_tool_schemas()),
        _schema_names(documents.document_tool_schemas()),
        _schema_names(validation.validation_tool_schemas()),
        _schema_names(approval.approval_tool_schemas()),
    )

    assert facade_names <= registry_names
    assert {"stock_overview", "lookup_evidence", "request_approval"} <= facade_names


def test_approval_schema_remains_high_risk_and_provider_owned() -> None:
    request_approval = [
        descriptor
        for descriptor in schemas.default_tool_descriptors()
        if descriptor.name == "request_approval"
    ][0]

    assert request_approval.category == ToolCategory.HIGH_RISK
    assert request_approval.metadata["approval_required"] is True
