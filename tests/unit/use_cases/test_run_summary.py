from doge.application.use_cases.run_summary import BuildRunSummary, redact_inaccessible_citations
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun, EventType, RunStatus
from doge.core.domain.evidence_models import EvidenceRecord


def test_build_run_summary_assembles_claims_citations_and_eval():
    run = AgentRun.create(workflow="investment_research", question="Analyze", run_id="run-1")
    run.status = RunStatus.COMPLETED
    artifact = AgentArtifact(
        artifact_id="art-1",
        run_id="run-1",
        kind="report",
        title="Report",
        content="Revenue grew 12%.",
        data={"claims": [{"claim_id": "claim-1", "text": "Revenue grew 12%.", "status": "supported"}]},
    )
    event = AgentEvent(
        event_id="evt-1",
        run_id="run-1",
        event_type=EventType.MODEL_RESPONSE,
        payload={"usage": {"prompt_tokens": 100, "cached_tokens": 25, "cost_usd": 0.01, "latency_ms": 1200}},
        sequence=1,
    )
    evidence = EvidenceRecord(
        evidence_id="evd-1",
        run_id="run-1",
        document_id="doc-1",
        page_id="page-1",
        chunk_id="chunk-1",
        page_number=3,
        claim="Revenue grew 12%.",
        support_snippet="The filing says revenue grew 12%.",
    )

    result = BuildRunSummary(_Runtime(run, [event], [artifact]), _EvidenceRepo([evidence])).build(run)

    assert result["summary"]["status"] == "current"
    assert result["summary"]["summary_text"] == "Revenue grew 12%."
    assert result["claims"][0]["support_status"] == "supported"
    assert result["citations"][0]["document_id"] == "doc-1"
    assert result["citations"][0]["accessible"] is True
    assert result["eval"]["coverage_ratio"] == 1.0
    assert result["eval"]["metrics"]["cost_usd"] == 0.01


def test_redact_inaccessible_citations_hides_snippets_and_marks_eval_failure():
    result = {
        "summary": {"summary_id": "sum-1"},
        "claims": [{"claim_id": "claim-1", "support_status": "supported"}],
        "citations": [{
            "citation_id": "cit-1",
            "claim_id": "claim-1",
            "document_id": "doc-denied",
            "snippet": "secret source text",
            "accessible": True,
        }],
        "eval": {"failed_checks": [], "coverage_ratio": 1.0, "accessible_citation_count": 1},
    }

    redacted = redact_inaccessible_citations(result, accessible_document_ids=set())

    assert redacted["citations"][0]["accessible"] is False
    assert redacted["citations"][0]["snippet"] == ""
    assert redacted["eval"]["accessible_citation_count"] == 0
    assert "inaccessible_citations" in redacted["eval"]["failed_checks"]
    assert redacted["eval"]["coverage_ratio"] == 0.0


class _Runtime:
    def __init__(self, run, events, artifacts):
        self._run = run
        self._events = events
        self._artifacts = artifacts

    def list_events(self, run_id):
        return self._events

    def list_artifacts(self, run_id):
        return self._artifacts


class _EvidenceRepo:
    def __init__(self, evidence):
        self._evidence = evidence

    def list_evidence(self, *, run_id=None, document_id=None, limit=20, tenant_id=None):
        return self._evidence[:limit]
