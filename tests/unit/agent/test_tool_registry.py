from doge.application.agent.tools import ToolRegistry, build_default_tool_registry


def test_unknown_tool_returns_structured_error():
    result = ToolRegistry().execute("missing", {})

    assert result.ok is False
    assert result.error == "unknown tool"


def test_default_registry_contains_core_demo_tools():
    registry = build_default_tool_registry()
    names = {schema["function"]["name"] for schema in registry.schemas}

    assert {
        "query_stock",
        "stock_overview",
        "rsrs_ranking",
        "market_breadth",
        "volume_anomalies",
        "list_views",
        "get_portfolio_exposure",
        "validate_financial_claims",
        "lookup_evidence",
        "request_approval",
    } == names


def test_portfolio_tool_reports_missing_configuration():
    registry = build_default_tool_registry()

    result = registry.execute("get_portfolio_exposure", {"portfolio_id": "portfolio-demo"})

    assert result.ok is False
    assert "not configured" in result.error


def test_lookup_evidence_returns_empty_when_library_absent(monkeypatch):
    from doge.application import composition

    class EmptyNotes:
        def search_notes(self, query, limit=50):
            return []

    monkeypatch.setattr(composition, "build_note_repository", lambda: EmptyNotes())
    registry = build_default_tool_registry()

    result = registry.execute("lookup_evidence", {"query": "earnings quality", "limit": 1})

    assert result.ok is True
    assert result.data["results"] == []
