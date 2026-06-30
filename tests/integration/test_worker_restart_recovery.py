"""Restart-recovery checks for persisted agent runtime execution."""

from __future__ import annotations

import pytest

from doge.application.tools import ToolRegistry, ToolResult
from doge.bootstrap.runtime import RuntimeContainer
from doge.core.domain.agent_models import EventType, RunStatus
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.database.agent_repositories import SQLiteEventRepository
from doge.shared.scope import TenantScope


def _schema(name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": name,
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _evidence_chunk() -> EvidenceChunk:
    return EvidenceChunk.create(
        document_id="doc-nvda-10k",
        page_number=42,
        chunk_id="chk-q2-revenue",
        text="NVDA reported revenue growth of 12% in the second quarter of fiscal 2025.",
        source_tool="stock_overview",
        run_id="run-test",
    )


def _registry_with_evidence(chunk: EvidenceChunk) -> ToolRegistry:
    registry = ToolRegistry()

    def stock_overview(**kwargs):
        return ToolResult(
            name="stock_overview",
            data={
                "ticker": kwargs.get("ticker", "NVDA"),
                "results": [{
                    "document_id": chunk.document_id,
                    "page_number": chunk.page_number,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                }],
            },
        )

    registry.register(_schema("stock_overview"), stock_overview)
    return registry


class ToolThenMemoModel:
    async def chat(self, messages, **kwargs):
        tool_results = [message for message in messages if message.role == "tool"]
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
            return
        yield AgentResponse(
            message=AgentMessage(
                role="assistant",
                content="NVDA revenue grew 12% in Q2 2025, leading the semiconductor sector.",
            ),
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        )


@pytest.mark.asyncio
async def test_fresh_runtime_kernel_rehydrates_tool_results_for_citations(tmp_path):
    db = tmp_path / "agent_state.db"
    registry = _registry_with_evidence(_evidence_chunk())

    kernel1 = RuntimeContainer(db).build_agent_runtime_kernel(
        model=ToolThenMemoModel(),
        tool_registry=registry,
    )
    run = await kernel1.create_run({"question": "Analyze NVDA revenue"})
    stepped = await kernel1.step(TenantScope.local(), run.run_id)

    assert stepped.status == RunStatus.RUNNING
    tool_results_after_tool = [
        event for event in SQLiteEventRepository(db).list_for_run(run.run_id)
        if event.event_type == EventType.TOOL_RESULT
    ]
    assert len(tool_results_after_tool) == 1
    assert tool_results_after_tool[0].payload["result"]["evidence_refs"]

    kernel2 = RuntimeContainer(db).build_agent_runtime_kernel(
        model=ToolThenMemoModel(),
        tool_registry=registry,
    )
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
