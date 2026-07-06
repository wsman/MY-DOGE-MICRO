import json

from doge.application.use_cases.demo_pack import DemoPackExporter
from doge.application.use_cases.run_summary import BuildRunSummary
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun, EventType, RunStatus
from doge.core.domain.evidence_models import EvidenceRecord


def test_demo_pack_exporter_writes_expected_files(tmp_path):
    run = AgentRun.create(workflow="investment_research", question="Analyze NVDA", run_id="run-1")
    run.status = RunStatus.COMPLETED
    artifact = AgentArtifact(
        artifact_id="art-1",
        run_id="run-1",
        kind="investment_memo",
        title="Investment Memo",
        content="Revenue grew 12%.",
        data={"claims": [{"claim_id": "claim-1", "text": "Revenue grew 12%.", "status": "supported"}]},
    )
    event = AgentEvent(
        event_id="evt-1",
        run_id="run-1",
        event_type=EventType.MODEL_RESPONSE,
        payload={"usage": {"cost_usd": 0.01}},
        sequence=1,
    )
    evidence = EvidenceRecord(
        evidence_id="evd-1",
        run_id="run-1",
        document_id="doc-1",
        page_id="page-1",
        chunk_id="chunk-1",
        page_number=2,
        claim="Revenue grew 12%.",
        support_snippet="Revenue grew 12%.",
    )
    runtime = _Runtime(run, [event], [artifact])

    result = DemoPackExporter(runtime, BuildRunSummary(runtime, _EvidenceRepo([evidence]))).export(
        "run-1",
        tmp_path / "packet",
    )

    assert sorted(result.files) == [
        "citations.json",
        "investment_memo.md",
        "metrics.json",
        "run_summary.md",
        "speaker_notes.md",
        "trace.jsonl",
    ]
    assert "# Run Summary - run-1" in result.files["run_summary.md"].read_text(encoding="utf-8")
    assert "Revenue grew 12%." in result.files["investment_memo.md"].read_text(encoding="utf-8")
    assert json.loads(result.files["trace.jsonl"].read_text(encoding="utf-8"))["event_id"] == "evt-1"
    assert json.loads(result.files["citations.json"].read_text(encoding="utf-8"))["citations"][0]["document_id"] == "doc-1"
    assert json.loads(result.files["metrics.json"].read_text(encoding="utf-8"))["run_id"] == "run-1"
    assert "This packet is local evidence" in result.files["speaker_notes.md"].read_text(encoding="utf-8")


def test_demo_pack_exporter_selects_investment_memo_when_later_artifact_exists(tmp_path):
    run = AgentRun.create(workflow="investment_research", question="Analyze NVDA", run_id="run-1")
    memo = AgentArtifact(
        artifact_id="art-1",
        run_id="run-1",
        kind="investment_memo",
        title="Investment Memo",
        content="Use this memo.",
    )
    later_artifact = AgentArtifact(
        artifact_id="art-2",
        run_id="run-1",
        kind="metrics",
        title="Metrics",
        content="Do not export as memo.",
    )
    runtime = _Runtime(run, [], [memo, later_artifact])

    result = DemoPackExporter(runtime, BuildRunSummary(runtime, _EvidenceRepo([]))).export(
        "run-1",
        tmp_path / "packet",
    )

    memo_text = result.files["investment_memo.md"].read_text(encoding="utf-8")
    assert "Use this memo." in memo_text
    assert "Do not export as memo." not in memo_text


class _Runtime:
    def __init__(self, run, events, artifacts):
        self._run = run
        self._events = events
        self._artifacts = artifacts

    def get_run(self, scope, run_id):
        assert run_id == "run-1"
        return self._run

    def list_events(self, scope, run_id):
        assert run_id == "run-1"
        return self._events

    def list_artifacts(self, scope, run_id):
        assert run_id == "run-1"
        return self._artifacts


class _EvidenceRepo:
    def __init__(self, evidence):
        self._evidence = evidence

    def list_evidence(self, *, scope=None, run_id=None, document_id=None, limit=20, tenant_id=None):
        return self._evidence[:limit]
