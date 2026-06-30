"""Restart-recovery unit coverage for RunStepper event-sourced tool results."""

from __future__ import annotations

from doge.application.agent.run_stepper import _tool_results_from_events
from doge.core.domain.agent_models import AgentEvent, EventType
from doge.core.domain.evidence_chunk_models import EvidenceChunk


def test_tool_results_from_events_rehydrates_persisted_evidence_refs():
    run_id = "run-restart"
    chunk = EvidenceChunk.create(
        document_id="doc-10k",
        page_number=7,
        chunk_id="chk-risk",
        text="Revenue grew 12% with margin pressure.",
        source_tool="stock_overview",
        run_id=run_id,
    )
    event = AgentEvent(
        event_id="evt-tool-result",
        run_id=run_id,
        event_type=EventType.TOOL_RESULT,
        sequence=3,
        payload={
            "tool_call_id": "tc-1",
            "name": "stock_overview",
            "result": {
                "ok": True,
                "name": "stock_overview",
                "data": {"ticker": "NVDA", "revenue_growth": 12},
                "error": None,
                "evidence_refs": [chunk.to_dict()],
            },
        },
    )

    results = _tool_results_from_events([event])

    assert len(results) == 1
    assert results[0].name == "stock_overview"
    assert results[0].data["ticker"] == "NVDA"
    assert results[0].evidence_refs is not None
    assert results[0].evidence_refs[0].evidence_id == chunk.evidence_id
    assert results[0].evidence_refs[0].run_id == run_id
