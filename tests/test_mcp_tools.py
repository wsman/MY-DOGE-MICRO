"""Tests for MCP server tools, validation, and lifecycle.

Retargeted (Batch-5) from the legacy ``mcp_server`` monolith to the modular
``doge.interfaces.mcp.server`` + ``doge.interfaces.mcp.tools`` packages. The
editable install (``pip install -e .``) resolves ``doge`` as a top-level
package, so no ``sys.path`` shim is needed here.
"""
import asyncio
import json
import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from doge.application import composition
from doge.config import reset_settings
from doge.core.domain.platform_models import Project, ResearchCase, Workspace
from doge.interfaces.mcp import server as srv

# The modular server builds the FastMCP instance lazily via a factory. Construct
# one at import time so tests that inspect the tool surface / SSE routes share a
# single configured server.
mcp = srv.create_mcp_server()


def _tool_text(result) -> str:
    """Extract the TextContent text from a FastMCP call_tool result.

    ``call_tool`` returns a ``(content_blocks, structured_dict)`` tuple. The
    MCP tools here always return a single TextContent as the first element, so
    coerce defensively.
    """
    if isinstance(result, str):
        return result
    # FastMCP returns (Sequence[ContentBlock], dict); take the first block.
    if isinstance(result, tuple) and result:
        result = result[0]
    if hasattr(result, "__iter__") and not isinstance(result, (dict, bytes)):
        blocks = list(result)
        if blocks and hasattr(blocks[0], "text"):
            return blocks[0].text
        if blocks and isinstance(blocks[0], dict) and "text" in blocks[0]:
            return blocks[0]["text"]
    if isinstance(result, dict) and "text" in result:
        return result["text"]
    return str(result)


# ── Validation ──────────────────────────────────────────

class TestValidateMarket:
    def test_valid_cn(self):
        assert srv._validate_market("cn") == "cn"
        assert srv._validate_market("CN") == "cn"

    def test_valid_us(self):
        assert srv._validate_market("us") == "us"
        assert srv._validate_market("US") == "us"

    def test_default_cn(self):
        assert srv._validate_market("") == "cn"
        assert srv._validate_market(None) == "cn"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid market"):
            srv._validate_market("xx")
        with pytest.raises(ValueError, match="Invalid market"):
            srv._validate_market("cn; DROP TABLE")


class TestValidateTicker:
    def test_valid_cn_6xxx(self):
        assert srv._validate_ticker("600000") == "600000.SH"

    def test_valid_cn_0xxx(self):
        assert srv._validate_ticker("000001") == "000001.SZ"

    def test_valid_cn_3xxx(self):
        assert srv._validate_ticker("300001") == "300001.SZ"

    def test_valid_cn_4xxx(self):
        assert srv._validate_ticker("430001") == "430001.BJ"

    def test_valid_cn_8xxx(self):
        assert srv._validate_ticker("830001") == "830001.BJ"

    def test_valid_with_suffix(self):
        assert srv._validate_ticker("000001.SZ") == "000001.SZ"

    def test_valid_us_ticker(self):
        assert srv._validate_ticker("AAPL") == "AAPL"

    def test_strip_whitespace(self):
        assert srv._validate_ticker("  600000  ") == "600000.SH"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="ticker is required"):
            srv._validate_ticker("")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="ticker is required"):
            srv._validate_ticker(None)

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            srv._validate_ticker("A" * 21)

    def test_invalid_chars_semicolon(self):
        with pytest.raises(ValueError, match="invalid characters"):
            srv._validate_ticker("600000; DROP TABLE")

    def test_invalid_chars_at_sign(self):
        with pytest.raises(ValueError, match="invalid characters"):
            srv._validate_ticker("600000@evil")

    def test_invalid_chars_unicode(self):
        with pytest.raises(ValueError, match="invalid characters"):
            srv._validate_ticker("6零零零零零")


class TestValidateInt:
    def test_within_range(self):
        assert srv._validate_int("days", 20, 1, 500) == 20

    def test_boundary(self):
        assert srv._validate_int("days", 1, 1, 500) == 1
        assert srv._validate_int("days", 500, 1, 500) == 500

    def test_below_min(self):
        with pytest.raises(ValueError, match="days"):
            srv._validate_int("days", 0, 1, 500)

    def test_above_max(self):
        with pytest.raises(ValueError, match="days"):
            srv._validate_int("days", 501, 1, 500)

    def test_non_int(self):
        with pytest.raises(ValueError, match="days"):
            srv._validate_int("days", "twenty", 1, 500)


class TestValidateFloat:
    def test_within_range(self):
        assert srv._validate_float("ratio", 3.5, 1.0, 1000.0) == 3.5

    def test_boundary(self):
        assert srv._validate_float("ratio", 1.0, 1.0, 1000.0) == 1.0

    def test_below_min(self):
        with pytest.raises(ValueError, match="ratio"):
            srv._validate_float("ratio", 0.5, 1.0, 1000.0)

    def test_above_max(self):
        with pytest.raises(ValueError, match="ratio"):
            srv._validate_float("ratio", 1001.0, 1.0, 1000.0)

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="ratio"):
            srv._validate_float("ratio", "three", 1.0, 1000.0)

    def test_int_accepted(self):
        assert srv._validate_float("ratio", 5, 1.0, 1000.0) == 5.0


# ── Formatting ──────────────────────────────────────────

class TestFormatHelper:
    def test_empty_rows_returns_empty_string(self):
        assert srv._fmt(["a", "b"], []) == ""

    def test_single_row(self):
        result = srv._fmt(["col1", "col2"], [[1, 2.5]])
        lines = result.split("\n")
        assert len(lines) == 2
        assert "col1" in lines[0]
        assert "2.50" in lines[1]

    def test_multiple_rows_alignment(self):
        result = srv._fmt(["a", "bb"], [[1, 2], [333, 4]])
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("a")

    def test_float_formatting_two_decimals(self):
        result = srv._fmt(["f"], [[3.14159]])
        assert "3.14" in result

    def test_none_values(self):
        result = srv._fmt(["x"], [[None]])
        assert "None" in result

    def test_wide_columns(self):
        result = srv._fmt(["short", "verylongcolumnname"], [[1, 2]])
        assert "short" in result
        assert "verylongcolumnname" in result


# ── Decorators ──────────────────────────────────────────

class TestTimedDecorator:
    @pytest.mark.asyncio
    async def test_success_records_metrics(self):
        orig_count = srv.REQUEST_COUNT.get("test_success_tool", 0)

        @srv._timed("test_success_tool")
        async def good_tool():
            return "ok"

        result = await good_tool()
        assert result == "ok"
        assert srv.REQUEST_COUNT["test_success_tool"] == orig_count + 1
        assert len(srv.REQUEST_DURATION["test_success_tool"]) > 0

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self):
        orig_timeout = srv.TOOL_TIMEOUT
        srv.TOOL_TIMEOUT = 0.05
        try:
            @srv._timed("test_timeout_tool")
            async def slow_tool():
                await asyncio.sleep(1)
                return "should not reach"

            result = await slow_tool()
            assert "timed out" in result
        finally:
            srv.TOOL_TIMEOUT = orig_timeout

    @pytest.mark.asyncio
    async def test_exception_returns_error_string(self):
        @srv._timed("test_exc_tool")
        async def bad_tool():
            raise RuntimeError("boom")

        result = await bad_tool()
        assert result == "Error: RuntimeError: boom"

    @pytest.mark.asyncio
    async def test_correlation_id_set(self):
        @srv._timed("test_cid_tool")
        async def cid_tool():
            return srv.correlation_id.get()

        result = await cid_tool()
        assert result != "-"
        assert len(result) == 8


# ── PID Manager ─────────────────────────────────────────

class TestPidManager:
    def test_register_appends_pid(self, tmp_path):
        orig_pid_file = srv.PID_FILE
        pid_file = tmp_path / "test.pid"
        srv.PID_FILE = pid_file
        try:
            srv._register_pid()
            assert pid_file.exists()
            content = pid_file.read_text()
            assert str(os.getpid()) in content
        finally:
            srv.PID_FILE = orig_pid_file

    def test_register_multiple(self, tmp_path):
        orig_pid_file = srv.PID_FILE
        pid_file = tmp_path / "test.pid"
        srv.PID_FILE = pid_file
        try:
            srv._register_pid()
            srv._register_pid()
            content = pid_file.read_text().strip().split("\n")
            assert content.count(str(os.getpid())) == 2
        finally:
            srv.PID_FILE = orig_pid_file

    def test_unregister_removes_all_same_pid(self, tmp_path):
        # _unregister_pid removes ALL instances of the current PID
        orig_pid_file = srv.PID_FILE
        pid_file = tmp_path / "test.pid"
        srv.PID_FILE = pid_file
        try:
            srv._register_pid()
            srv._register_pid()
            srv._unregister_pid()
            # All instances of current PID are removed, so file should be gone
            assert not pid_file.exists()
        finally:
            srv.PID_FILE = orig_pid_file

    def test_unregister_last_removes_file(self, tmp_path):
        orig_pid_file = srv.PID_FILE
        pid_file = tmp_path / "test.pid"
        srv.PID_FILE = pid_file
        try:
            srv._register_pid()
            srv._unregister_pid()
            assert not pid_file.exists()
        finally:
            srv.PID_FILE = orig_pid_file

    def test_unregister_missing_file_no_crash(self):
        orig_pid_file = srv.PID_FILE
        srv.PID_FILE = Path("/nonexistent/path/test.pid")
        try:
            srv._unregister_pid()
        finally:
            srv.PID_FILE = orig_pid_file


# ── Tool Presence ───────────────────────────────────────

class TestToolsNotPresent:
    @pytest.mark.asyncio
    async def test_run_sql_removed(self):
        tools = await mcp.list_tools()
        names = [t.name for t in tools]
        assert "run_sql" not in names

    @pytest.mark.asyncio
    async def test_expected_tools_present(self):
        tools = await mcp.list_tools()
        names = [t.name for t in tools]
        expected = {"query_stock", "stock_overview", "rsrs_ranking",
                    "market_breadth", "volume_anomalies", "list_views",
                    "seed_workflow_templates", "list_workflow_templates",
                    "show_workflow_template", "list_research_cases",
                    "preflight_case_execution", "execute_case_template",
                    "record_case_decision"}
        assert expected.issubset(set(names))

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self):
        tools = await mcp.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} lacks description"

    @pytest.mark.asyncio
    async def test_tools_descriptions_are_chinese(self):
        tools = await mcp.list_tools()
        for tool in tools:
            assert any("一" <= c <= "鿿" for c in tool.description), \
                f"Tool {tool.name} description is not Chinese: {tool.description}"


# ── Mock-backed Tool Logic ──────────────────────────────

class TestQueryStockMock:
    @pytest.mark.asyncio
    async def test_invalid_market(self, monkeypatch):
        async def mock_impl(*args, **kwargs):
            return "should not reach"

        monkeypatch.setattr(srv, "query_stock", mock_impl)
        with pytest.raises(ValueError, match="Invalid market"):
            srv._validate_market("xx")

    def test_invalid_ticker_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            srv._validate_ticker("1; DROP TABLE")


class TestPlatformWorkflowTools:
    @pytest.mark.asyncio
    async def test_case_template_preflight_execute_and_decision(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
        monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "true")
        reset_settings()
        repo = composition.build_platform_repository()
        workspace = Workspace.create(name="Desk")
        project = Project.create(workspace_id=workspace.workspace_id, name="Research")
        case = ResearchCase.create(project_id=project.project_id, title="NVDA earnings")
        repo.save_workspace(workspace)
        repo.save_project(project)
        repo.save_case(case)

        seed = json.loads(_tool_text(await mcp.call_tool("seed_workflow_templates", {})))
        preflight = json.loads(_tool_text(await mcp.call_tool(
            "preflight_case_execution",
            {
                "case_id": case.case_id,
                "template_id": "earnings_review",
                "inputs": {"ticker": "NVDA", "reporting_period": "2026Q1"},
            },
        )))
        execution = json.loads(_tool_text(await mcp.call_tool(
            "execute_case_template",
            {
                "case_id": case.case_id,
                "template_id": "earnings_review",
                "inputs": {"ticker": "NVDA", "reporting_period": "2026Q1"},
            },
        )))
        decision = json.loads(_tool_text(await mcp.call_tool(
            "record_case_decision",
            {
                "case_id": case.case_id,
                "decision_type": "approve",
                "rationale": "Supported",
                "source_run_ids": [execution["run_id"]],
            },
        )))

        assert "earnings_review" in seed["inserted"]
        assert preflight["valid"] is True
        assert execution["execution_id"].startswith("exec-")
        assert execution["run_id"].startswith("run-")
        assert decision["decision_type"] == "approve"


# ── Integration Tests (Real DB) ─────────────────────────

class TestQueryStockIntegration:
    @pytest.mark.asyncio
    async def test_query_stock_cn_success(self):
        result = await srv.query_stock("600000", "cn", 5)
        assert isinstance(result, str)
        assert "No data" not in result
        lines = result.split("\n")
        assert len(lines) >= 2

    @pytest.mark.asyncio
    async def test_query_stock_us_success(self):
        result = await srv.query_stock("AAPL", "us", 5)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_query_stock_no_data(self):
        result = await srv.query_stock("999999.SH", "cn", 5)
        assert "No data" in result

    @pytest.mark.asyncio
    async def test_query_stock_invalid_market(self):
        # Routed through the registered MCP tool so the server wrapper's
        # validation + _timed decorator catches ValueError and returns an
        # error string (the raw impl does not validate market itself).
        result = await mcp.call_tool("query_stock", {"ticker": "600000", "market": "xx", "days": 5})
        text = _tool_text(result)
        assert text.startswith("Error:")
        assert "Invalid market" in text

    @pytest.mark.asyncio
    async def test_query_stock_days_boundary(self):
        result = await srv.query_stock("600000", "cn", 1)
        lines = result.split("\n")
        assert len(lines) == 2


class TestStockOverviewIntegration:
    @pytest.mark.asyncio
    async def test_overview_cn(self):
        result = await srv.stock_overview("600000", "cn")
        assert isinstance(result, str)
        assert "600000" in result
        assert "CN" in result

    @pytest.mark.asyncio
    async def test_overview_us(self):
        result = await srv.stock_overview("AAPL", "us")
        assert isinstance(result, str)
        assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_overview_no_data(self):
        result = await srv.stock_overview("999999.SH", "cn")
        assert isinstance(result, str)
        assert "999999.SH" in result


class TestRsrsRankingIntegration:
    @pytest.mark.asyncio
    async def test_rsrs_cn(self):
        result = await srv.rsrs_ranking("cn", 10)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_rsrs_us(self):
        result = await srv.rsrs_ranking("us", 10)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_rsrs_top_limit(self):
        result = await srv.rsrs_ranking("cn", 5)
        lines = result.strip().split("\n")
        assert len(lines) <= 6


class TestMarketBreadthIntegration:
    @pytest.mark.asyncio
    async def test_breadth_cn(self):
        result = await srv.market_breadth("cn", 5)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_breadth_us(self):
        result = await srv.market_breadth("us", 5)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_breadth_days_boundary(self):
        result = await srv.market_breadth("cn", 1)
        lines = result.strip().split("\n")
        assert len(lines) <= 2


class TestVolumeAnomaliesIntegration:
    @pytest.mark.asyncio
    async def test_volume_anomalies_default(self):
        result = await srv.volume_anomalies(3.0, 10)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_volume_anomalies_low_ratio(self):
        result = await srv.volume_anomalies(1.0, 5)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_volume_anomalies_invalid_ratio(self):
        # Routed through the registered MCP tool so the server wrapper's
        # validation + _timed decorator catches ValueError and returns an
        # error string (the raw impl does not validate min_ratio itself).
        result = await mcp.call_tool("volume_anomalies", {"min_ratio": 0.5, "top": 10})
        text = _tool_text(result)
        assert text.startswith("Error:")
        assert "min_ratio" in text


class TestListViewsIntegration:
    @pytest.mark.asyncio
    async def test_list_views_returns_json(self):
        result = await srv.list_views()
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_views_contains_known_views(self):
        result = await srv.list_views()
        data = json.loads(result)
        view_names = {item["view"] for item in data}
        expected = {
            "vw_daily_enriched_cn",
            "vw_market_breadth_cn",
            "vw_rsrs_ranking_cn",
            "vw_volume_anomalies_cn",
            "vw_cross_sectional_return_cn",
            "vw_market_breadth_us",
            "vw_rsrs_ranking_us",
        }
        assert expected.issubset(view_names), f"Missing views: {expected - view_names}"


# ── SSE Routes ──────────────────────────────────────────

class TestSseRoutes:
    def test_health_ok(self):
        app = mcp.sse_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_duckdb_failure(self, monkeypatch):
        # The modular /health route opens a DuckDB connection via
        # ``DuckDBConnection(...).connect()`` inside the handler. Patch the
        # connection method so the route reports 503 on DB failure.
        from doge.infrastructure.database import duckdb as duckdb_mod

        class _BoomConn:
            def __init__(self, *a, **kw):
                pass

            def connect(self):
                raise RuntimeError("db down")

        monkeypatch.setattr(duckdb_mod, "DuckDBConnection", _BoomConn)
        app = mcp.sse_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["status"] == "error"

    def test_metrics_empty(self):
        orig_count = dict(srv.REQUEST_COUNT)
        orig_duration = {k: list(v) for k, v in srv.REQUEST_DURATION.items()}
        srv.REQUEST_COUNT.clear()
        srv.REQUEST_DURATION.clear()
        try:
            app = mcp.sse_app()
            client = TestClient(app)
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "# no metrics yet" in response.json()["metrics"]
        finally:
            srv.REQUEST_COUNT.update(orig_count)
            srv.REQUEST_DURATION.update(orig_duration)

    def test_metrics_with_data(self):
        orig_count = dict(srv.REQUEST_COUNT)
        orig_duration = {k: list(v) for k, v in srv.REQUEST_DURATION.items()}
        srv.REQUEST_COUNT.clear()
        srv.REQUEST_DURATION.clear()
        srv.REQUEST_COUNT["test_tool"] = 3
        srv.REQUEST_DURATION["test_tool"] = [0.1, 0.2, 0.3]
        try:
            app = mcp.sse_app()
            client = TestClient(app)
            response = client.get("/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]
            assert 'mcp_requests_total{tool="test_tool"} 3' in metrics
            assert 'mcp_request_duration_seconds_sum{tool="test_tool"}' in metrics
            assert 'mcp_request_duration_seconds_count{tool="test_tool"} 3' in metrics
        finally:
            srv.REQUEST_COUNT.clear()
            srv.REQUEST_COUNT.update(orig_count)
            srv.REQUEST_DURATION.clear()
            srv.REQUEST_DURATION.update(orig_duration)
