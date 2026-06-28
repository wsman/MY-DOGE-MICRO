"""Unit tests for ToolExecutionService evidence_refs wiring."""

from __future__ import annotations

import pytest

from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.core.ports.runtime_services import ToolResult
from doge.platform.runtime.services import ToolExecutionService, _build_evidence_chunks


class FakeToolRegistry:
    """Registry that returns pre-configured ToolResults."""

    def __init__(self, results: dict[str, ToolResult] | None = None):
        self._results = results or {}
        self.calls: list[dict[str, object]] = []

    async def execute_async(
        self,
        name: str,
        arguments: str,
        *,
        timeout_seconds: float | None = None,
        context: object = None,
    ) -> ToolResult:
        self.calls.append({"name": name, "arguments": arguments, "context": context})
        return self._results.get(name, ToolResult(name=name, data={}))


class FakeGovernanceRepository(IEnterpriseGovernanceRepository):
    def __init__(self):
        self._grants: set[tuple[str, str, str, str]] = set()
        self.audit_events: list[object] = []

    def grant(self, grant: object) -> None:
        self._grants.add((
            grant.tenant_id,
            grant.subject_hash,
            grant.resource_type,
            grant.resource_id,
        ))

    def is_allowed(self, context: object, resource_type: str, resource_id: str, permission: str) -> bool:
        return (context.tenant_id, context.user_hash, resource_type, resource_id) in self._grants

    def append_audit_event(self, event: object) -> None:
        self.audit_events.append(event)

    def list_audit_events(self, tenant_id: str) -> list[object]:
        return [e for e in self.audit_events if getattr(e, "tenant_id", None) == tenant_id]


@pytest.fixture
def tool_registry():
    return FakeToolRegistry()


@pytest.fixture
def governance_repository():
    return FakeGovernanceRepository()


class TestBuildEvidenceChunks:
    """Tests for the _build_evidence_chunks helper."""

    def test_empty_list_for_failed_tool(self):
        raw = ToolResult(name="market_breadth", data={}, ok=False, error="timeout")
        chunks = _build_evidence_chunks(raw, run_id="run-1")
        assert chunks == []

    def test_single_chunk_for_numeric_output(self):
        raw = ToolResult(name="stock_overview", data={"ticker": "AAPL", "price": 150.0})
        chunks = _build_evidence_chunks(raw, run_id="run-1")

        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.source_tool == "stock_overview"
        assert chunk.run_id == "run-1"
        assert chunk.document_id == "stock_overview"
        assert chunk.chunk_id == "stock_overview-output"
        assert chunk.page_number == 1
        assert '"ticker": "AAPL"' in chunk.text
        assert chunk.evidence_id.startswith("evd-")

    def test_multiple_chunks_from_evidence_list(self):
        raw = ToolResult(
            name="lookup_evidence",
            data={
                "results": [
                    {"document_id": "doc-1", "chunk_id": "chk-1", "page_number": 3, "text": "Revenue grew 12%."},
                    {"document_id": "doc-2", "chunk_id": "chk-2", "page_number": 5, "text": "Margins stable."},
                ]
            },
        )
        chunks = _build_evidence_chunks(raw, run_id="run-2")

        assert len(chunks) == 2
        assert chunks[0].document_id == "doc-1"
        assert chunks[0].chunk_id == "chk-1"
        assert chunks[0].page_number == 3
        assert chunks[0].text == "Revenue grew 12%."
        assert chunks[0].run_id == "run-2"
        assert chunks[1].document_id == "doc-2"
        assert chunks[1].page_number == 5

    def test_multiple_chunks_from_evidence_key(self):
        raw = ToolResult(
            name="lookup_evidence",
            data={
                "evidence": [
                    {"document_id": "doc-a", "chunk_id": "c-a", "text": "Claim A"},
                ]
            },
        )
        chunks = _build_evidence_chunks(raw, run_id="run-3")

        assert len(chunks) == 1
        assert chunks[0].document_id == "doc-a"
        assert chunks[0].text == "Claim A"

    def test_empty_list_when_no_data(self):
        raw = ToolResult(name="noop", data={})
        chunks = _build_evidence_chunks(raw, run_id="run-4")
        assert chunks == []

    def test_stable_id_for_same_inputs(self):
        raw = ToolResult(name="stock_overview", data={"price": 100.0})
        chunks_a = _build_evidence_chunks(raw, run_id="run-5")
        chunks_b = _build_evidence_chunks(raw, run_id="run-5")

        assert len(chunks_a) == 1
        assert len(chunks_b) == 1
        assert chunks_a[0].evidence_id == chunks_b[0].evidence_id

    def test_different_ids_for_different_runs(self):
        raw = ToolResult(name="stock_overview", data={"price": 100.0})
        chunks_a = _build_evidence_chunks(raw, run_id="run-a")
        chunks_b = _build_evidence_chunks(raw, run_id="run-b")

        assert chunks_a[0].evidence_id != chunks_b[0].evidence_id


class TestToolExecutionServiceEvidenceRefs:
    """Tests for ToolExecutionService.execute wiring evidence_refs."""

    @pytest.mark.asyncio
    async def test_execute_returns_none_evidence_refs_for_empty_tool_output(self, tool_registry):
        service = ToolExecutionService(tool_registry=tool_registry)
        result = await service.execute(
            context=None,
            tool_name="noop",
            arguments="{}",
            run_id="run-1",
            timeout_seconds=None,
            request_id=None,
        )
        assert result.evidence_refs is None

    @pytest.mark.asyncio
    async def test_execute_populates_evidence_refs_for_numeric_output(self, tool_registry):
        tool_registry._results["stock_overview"] = ToolResult(
            name="stock_overview",
            data={"ticker": "AAPL", "price": 150.0},
        )
        service = ToolExecutionService(tool_registry=tool_registry)
        result = await service.execute(
            context=None,
            tool_name="stock_overview",
            arguments='{"ticker":"AAPL"}',
            run_id="run-1",
            timeout_seconds=None,
            request_id=None,
        )
        assert result.evidence_refs is not None
        assert len(result.evidence_refs) == 1
        assert result.evidence_refs[0].source_tool == "stock_overview"
        assert result.evidence_refs[0].run_id == "run-1"

    @pytest.mark.asyncio
    async def test_execute_populates_evidence_refs_for_evidence_list(self, tool_registry):
        tool_registry._results["lookup_evidence"] = ToolResult(
            name="lookup_evidence",
            data={
                "results": [
                    {"document_id": "doc-1", "chunk_id": "chk-1", "page_number": 2, "text": "Fact 1"},
                    {"document_id": "doc-1", "chunk_id": "chk-2", "page_number": 3, "text": "Fact 2"},
                ]
            },
        )
        service = ToolExecutionService(tool_registry=tool_registry)
        result = await service.execute(
            context=None,
            tool_name="lookup_evidence",
            arguments='{"query":"test"}',
            run_id="run-2",
            timeout_seconds=None,
            request_id=None,
        )
        assert result.evidence_refs is not None
        assert len(result.evidence_refs) == 2
        assert result.evidence_refs[0].text == "Fact 1"
        assert result.evidence_refs[1].text == "Fact 2"

    @pytest.mark.asyncio
    async def test_execute_returns_none_evidence_refs_for_denied_tool(self, tool_registry, governance_repository):
        context = EnterpriseContext(
            tenant_id="tenant-a",
            user_hash="user-a",
            tool_entitlement=frozenset(),
        )
        service = ToolExecutionService(
            tool_registry=tool_registry,
            governance_repository=governance_repository,
        )
        result = await service.execute(
            context=context,
            tool_name="forbidden_tool",
            arguments="{}",
            run_id="run-3",
            timeout_seconds=None,
            request_id=None,
        )
        assert result.ok is False
        assert result.error == "tool not permitted"
        assert result.evidence_refs is None

    @pytest.mark.asyncio
    async def test_execute_rebuilds_evidence_refs_from_raw_data(self, tool_registry):
        """When the raw tool result already carries evidence_refs, the service
        rebuilds them from the data payload so the run_id is always correct."""
        tool_registry._results["custom_tool"] = ToolResult(
            name="custom_tool",
            data={"value": 42},
            evidence_refs=[
                EvidenceChunk.create(
                    document_id="doc-pre",
                    page_number=1,
                    chunk_id="pre-1",
                    text="Pre-existing",
                    source_tool="custom_tool",
                    run_id="old-run",
                )
            ],
        )
        service = ToolExecutionService(tool_registry=tool_registry)
        result = await service.execute(
            context=None,
            tool_name="custom_tool",
            arguments="{}",
            run_id="run-4",
            timeout_seconds=None,
            request_id=None,
        )
        # Service rebuilds from data; old evidence_refs are discarded.
        assert result.evidence_refs is not None
        assert len(result.evidence_refs) == 1
        assert result.evidence_refs[0].run_id == "run-4"
        assert '"value": 42' in result.evidence_refs[0].text

    @pytest.mark.asyncio
    async def test_tool_result_json_includes_evidence_refs(self, tool_registry):
        tool_registry._results["stock_overview"] = ToolResult(
            name="stock_overview",
            data={"ticker": "AAPL"},
        )
        service = ToolExecutionService(tool_registry=tool_registry)
        result = await service.execute(
            context=None,
            tool_name="stock_overview",
            arguments="{}",
            run_id="run-5",
            timeout_seconds=None,
            request_id=None,
        )
        json_str = result.to_json()
        assert "evidence_refs" in json_str
        import json

        parsed = json.loads(json_str)
        assert parsed["evidence_refs"][0]["source_tool"] == "stock_overview"
        assert parsed["evidence_refs"][0]["run_id"] == "run-5"

    @pytest.mark.asyncio
    async def test_tool_result_json_omits_evidence_refs_when_none(self, tool_registry):
        tool_registry._results["noop"] = ToolResult(name="noop", data={})
        service = ToolExecutionService(tool_registry=tool_registry)
        result = await service.execute(
            context=None,
            tool_name="noop",
            arguments="{}",
            run_id="run-6",
            timeout_seconds=None,
            request_id=None,
        )
        json_str = result.to_json()
        import json

        parsed = json.loads(json_str)
        assert "evidence_refs" not in parsed
