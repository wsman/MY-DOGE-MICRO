"""Integration test for citation assembly end-to-end through RuntimeKernel."""

from __future__ import annotations

import pytest

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_citation_assembler import ArtifactCitationAssembler
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry, ToolResult
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.application.services.citation_service import CitationService
from doge.application.services.claim_validation_service import ClaimValidationService
from doge.application.services.citation_support_classifier import CitationSupportClassifier
from doge.core.domain.agent_models import EventType, RunStatus
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.core.ports.runtime_services import ModelExecutionResult
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteRuntimeTransactionFactory
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)
from doge.shared.scope import TenantScope


def _schema(name: str, description: str = ""):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description or name,
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _build_kernel_with_citations(db, model, tool_registry, evidence_repository):
    """Build a RuntimeKernel with citation assembler wired in."""
    response_assembler = ModelResponseAssembler()
    model_execution_service = ModelExecutionService(
        model=model,
        response_assembler=response_assembler,
        model_router=None,
        web_search_stage=None,
        agent_backends=None,
    )
    tool_execution_service = ToolExecutionService(
        tool_registry=tool_registry,
        governance_repository=None,
    )
    artifact_evaluation_service = ArtifactEvaluationService()

    repos = {
        "runs": SQLiteRunRepository(db),
        "events": SQLiteEventRepository(db),
        "artifacts": SQLiteArtifactRepository(db),
        "approvals": SQLiteApprovalRepository(db),
    }
    transition_recorder = TransitionRecorder(
        transaction_factory=SQLiteRuntimeTransactionFactory(db),
    )
    artifact_finalizer = ArtifactFinalizer(
        evaluation_service=artifact_evaluation_service,
    )
    context_builder = ContextBuilder(
        document_repository=None,
        evidence_repository=evidence_repository,
        session_repository=None,
        run_repository=repos["runs"],
    )
    citation_assembler = ArtifactCitationAssembler(
        evidence_repository=evidence_repository,
        citation_service=CitationService(),
        claim_validation_service=ClaimValidationService(),
        classifier=CitationSupportClassifier(),
    )
    stepper = RunStepper(
        run_repository=repos["runs"],
        event_repository=repos["events"],
        artifact_repository=repos["artifacts"],
        approval_repository=repos["approvals"],
        context_builder=context_builder,
        response_assembler=response_assembler,
        model_execution_service=model_execution_service,
        tool_execution_service=tool_execution_service,
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
        citation_assembler=citation_assembler,
    )
    lifecycle = RunLifecycleService(
        run_repository=repos["runs"],
        event_repository=repos["events"],
        artifact_repository=repos["artifacts"],
        approval_repository=repos["approvals"],
        transition_recorder=transition_recorder,
        run_stepper=stepper,
    )
    approval_coordinator = ApprovalCoordinator(
        run_repository=repos["runs"],
        approval_repository=repos["approvals"],
        transition_recorder=transition_recorder,
    )
    return RuntimeKernel(
        lifecycle_service=lifecycle,
        stepper=stepper,
        transition_recorder=transition_recorder,
        approval_coordinator=approval_coordinator,
        artifact_finalizer=artifact_finalizer,
    )


class FinalMemoModel:
    """Model that returns a final memo with claim-worthy content on first turn."""

    async def chat(self, messages, **kwargs):
        yield AgentResponse(
            message=AgentMessage(
                role="assistant",
                content="NVDA revenue grew 12% in Q2 2025, leading the semiconductor sector.",
            ),
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        )


class ToolThenMemoModel:
    """Model that calls a tool then returns a memo with claims on second turn."""

    async def chat(self, messages, **kwargs):
        tool_results = [m for m in messages if m.role == "tool"]
        if not tool_results:
            yield AgentResponse(
                message=AgentMessage(
                    role="assistant",
                    content="",
                    tool_calls=[{
                        "id": "tc-1",
                        "type": "function",
                        "function": {
                            "name": "stock_overview",
                            "arguments": '{"ticker":"NVDA"}',
                        },
                    }],
                )
            )
        else:
            yield AgentResponse(
                message=AgentMessage(
                    role="assistant",
                    content="NVDA revenue grew 12% in Q2 2025, leading the semiconductor sector.",
                ),
                finish_reason="stop",
                usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
            )


def _evidence_chunk():
    return EvidenceChunk.create(
        document_id="doc-nvda-10k",
        page_number=42,
        chunk_id="chk-q2-revenue",
        text="NVDA reported revenue growth of 12% in the second quarter of fiscal 2025.",
        source_tool="stock_overview",
        run_id="run-test",
    )


def _evidence_record(chunk: EvidenceChunk):
    """Convert EvidenceChunk to EvidenceRecord for repository storage."""
    from doge.core.domain.chunk_models import DocumentChunk as DocChunk
    doc_chunk = DocChunk(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        page_id=f"page-{chunk.page_number}",
        page_number=chunk.page_number,
        text=chunk.text,
        start_char=0,
        end_char=len(chunk.text),
    )
    return EvidenceRecord.create(
        chunk=doc_chunk,
        support_snippet=chunk.text,
        claim="NVDA revenue grew 12% in Q2 2025.",
        run_id=chunk.run_id,
    )


def _registry_with_evidence(evidence_chunk: EvidenceChunk):
    """Tool registry that returns tool results with evidence in data['results']."""
    registry = ToolRegistry()

    def stock_overview(**kwargs):
        return ToolResult(
            name="stock_overview",
            data={
                "ticker": kwargs.get("ticker", "NVDA"),
                "revenue_growth": 12.0,
                "results": [{
                    "document_id": evidence_chunk.document_id,
                    "page_number": evidence_chunk.page_number,
                    "chunk_id": evidence_chunk.chunk_id,
                    "text": evidence_chunk.text,
                }],
            },
        )

    registry.register(_schema("stock_overview", "Get stock overview"), stock_overview)
    return registry


@pytest.mark.asyncio
async def test_citation_assembly_kernel_final_artifact_has_inline_citations_and_sources_section(tmp_path):
    """End-to-end: RuntimeKernel with citation assembler produces inline citations and Sources section."""
    db = tmp_path / "agent_state.db"
    evidence_repo = SQLiteEvidenceRepository(db)

    model = FinalMemoModel()
    registry = ToolRegistry()
    registry.register(
        _schema("stock_overview", "Get stock overview"),
        lambda **_: ToolResult("stock_overview", {"ticker": "NVDA"}),
    )
    kernel = _build_kernel_with_citations(db, model, registry, evidence_repo)

    run = await kernel.create_run({"question": "Analyze NVDA revenue"})
    # Store evidence with the actual run_id after creation
    chunk = _evidence_chunk()
    record = _evidence_record(chunk)
    # Create a new record with the actual run_id
    from doge.core.domain.chunk_models import DocumentChunk as DocChunk
    doc_chunk = DocChunk(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        page_id=f"page-{chunk.page_number}",
        page_number=chunk.page_number,
        text=chunk.text,
        start_char=0,
        end_char=len(chunk.text),
    )
    record_with_run = EvidenceRecord.create(
        chunk=doc_chunk,
        support_snippet=chunk.text,
        claim="NVDA revenue grew 12% in Q2 2025.",
        run_id=run.run_id,
    )
    evidence_repo.save_evidence(record_with_run, TenantScope.local())

    completed = await kernel.run_to_pause_or_completion(run.run_id)

    assert completed.status == RunStatus.COMPLETED
    assert len(completed.artifacts) == 1
    artifact = completed.artifacts[0]
    # Inline citation markers should be present
    assert "[^evd-" in artifact.content or "## Sources" in artifact.content
    # Sources section should be present
    assert "## Sources" in artifact.content
    # Structured data should contain claims, citations, relations
    assert "claims" in artifact.data
    assert "citations" in artifact.data
    assert "relations" in artifact.data
    assert len(artifact.data["claims"]) > 0
    assert len(artifact.data["citations"]) > 0
    assert len(artifact.data["relations"]) > 0


@pytest.mark.asyncio
async def test_citation_assembly_kernel_tool_results_passed_to_assembler(tmp_path):
    """End-to-end: tool results with evidence_refs flow through to citation assembler."""
    db = tmp_path / "agent_state.db"
    evidence_repo = SQLiteEvidenceRepository(db)
    chunk = _evidence_chunk()

    model = ToolThenMemoModel()
    registry = _registry_with_evidence(chunk)
    kernel = _build_kernel_with_citations(db, model, registry, evidence_repo)

    run = await kernel.create_run({"question": "Analyze NVDA revenue"})
    # First step: tool call
    stepped = await kernel.step(TenantScope.local(), run.run_id)
    assert stepped.status == RunStatus.RUNNING
    assert any(e.event_type == EventType.TOOL_RESULT for e in stepped.events)
    # Second step: final memo with citations
    completed = await kernel.step(TenantScope.local(), run.run_id)
    assert completed.status == RunStatus.COMPLETED
    assert len(completed.artifacts) == 1
    artifact = completed.artifacts[0]
    # Should have inline citations and Sources section
    assert "[^evd-" in artifact.content or "## Sources" in artifact.content
    assert "## Sources" in artifact.content
    # Claims should be backed by evidence from tool results
    assert artifact.data["claims"]
    assert artifact.data["citations"]
    assert artifact.data["relations"]
    # At least one claim should be supported
    supported = [c for c in artifact.data["claims"] if c.get("status") == "supported"]
    assert len(supported) > 0


@pytest.mark.asyncio
async def test_citation_assembly_rehydrates_tool_results_after_fresh_kernel(tmp_path):
    """A fresh RunStepper must rebuild citation inputs from persisted TOOL_RESULT events."""
    db = tmp_path / "agent_state.db"
    chunk = _evidence_chunk()
    registry = _registry_with_evidence(chunk)

    kernel1 = _build_kernel_with_citations(db, ToolThenMemoModel(), registry, SQLiteEvidenceRepository(db))
    run = await kernel1.create_run({"question": "Analyze NVDA revenue"})

    stepped = await kernel1.step(TenantScope.local(), run.run_id)

    assert stepped.status == RunStatus.RUNNING
    persisted_after_tool = SQLiteEventRepository(db).list_for_run(run.run_id)
    tool_results_after_tool = [
        event for event in persisted_after_tool
        if event.event_type == EventType.TOOL_RESULT
    ]
    assert len(tool_results_after_tool) == 1
    assert tool_results_after_tool[0].payload["result"]["evidence_refs"]

    kernel2 = _build_kernel_with_citations(db, ToolThenMemoModel(), registry, SQLiteEvidenceRepository(db))

    completed = await kernel2.step(TenantScope.local(), run.run_id)

    assert completed.status == RunStatus.COMPLETED
    assert len(completed.artifacts) == 1
    artifact = completed.artifacts[0]
    assert "## Sources" in artifact.content
    assert artifact.data["citations"]
    assert artifact.data["relations"]
    assert [
        event for event in SQLiteEventRepository(db).list_for_run(run.run_id)
        if event.event_type == EventType.TOOL_RESULT
    ] == tool_results_after_tool


@pytest.mark.asyncio
async def test_citation_assembly_kernel_preserves_claims_in_artifact_data(tmp_path):
    """Artifact data from citation assembler is preserved in the final artifact."""
    db = tmp_path / "agent_state.db"
    evidence_repo = SQLiteEvidenceRepository(db)

    model = FinalMemoModel()
    registry = ToolRegistry()
    registry.register(
        _schema("stock_overview", "Get stock overview"),
        lambda **_: ToolResult("stock_overview", {"ticker": "NVDA"}),
    )
    kernel = _build_kernel_with_citations(db, model, registry, evidence_repo)

    run = await kernel.create_run({"question": "Analyze NVDA revenue"})
    # Store evidence with the actual run_id after creation
    chunk = _evidence_chunk()
    from doge.core.domain.chunk_models import DocumentChunk as DocChunk
    doc_chunk = DocChunk(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        page_id=f"page-{chunk.page_number}",
        page_number=chunk.page_number,
        text=chunk.text,
        start_char=0,
        end_char=len(chunk.text),
    )
    record_with_run = EvidenceRecord.create(
        chunk=doc_chunk,
        support_snippet=chunk.text,
        claim="NVDA revenue grew 12% in Q2 2025.",
        run_id=run.run_id,
    )
    evidence_repo.save_evidence(record_with_run, TenantScope.local())

    completed = await kernel.run_to_pause_or_completion(run.run_id)

    artifact = completed.artifacts[0]
    # Verify all assembler-produced fields are present
    assert "support_status" in artifact.data
    assert "coverage_ratio" in artifact.data
    assert isinstance(artifact.data["coverage_ratio"], float)
    assert 0.0 <= artifact.data["coverage_ratio"] <= 1.0
    # Verify claims have expected structure
    for claim in artifact.data["claims"]:
        assert "claim_id" in claim
        assert "text" in claim
        assert "status" in claim
    # Verify citations have expected structure
    for citation in artifact.data["citations"]:
        assert "citation_id" in citation
        assert "claim_id" in citation
        assert "snippet" in citation
        assert "document_id" in citation
    # Verify relations have expected structure
    for relation in artifact.data["relations"]:
        assert "relation_id" in relation
        assert "claim_id" in relation
        assert "evidence_id" in relation
        assert "support_status" in relation
        assert "confidence" in relation
