import pytest

from doge.application.use_cases.run_summary import BuildRunSummary
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun, EventType, RunStatus
from doge.interfaces.cli.main import main


def test_cli_demo_pack_exports_packet(tmp_path, monkeypatch, capsys):
    import doge.interfaces.cli.commands.demo_pack as demo_pack_command

    run = AgentRun.create(workflow="investment_research", question="Analyze", run_id="run-1")
    run.status = RunStatus.COMPLETED
    artifact = AgentArtifact(
        artifact_id="art-1",
        run_id="run-1",
        kind="investment_memo",
        title="Memo",
        content="Memo body",
    )
    event = AgentEvent("evt-1", "run-1", EventType.RUN_CREATED, sequence=1)
    runtime = _Runtime(run, [event], [artifact])
    monkeypatch.setattr(demo_pack_command, "_runtime_container", lambda: _Container(runtime))
    output = tmp_path / "demo_packet"

    main(["demo-pack", "--run-id", "run-1", "--output", str(output)])

    out = capsys.readouterr().out
    assert f"demo_pack={output}" in out
    assert (output / "run_summary.md").exists()
    assert (output / "investment_memo.md").read_text(encoding="utf-8").startswith("# Memo")


def test_cli_demo_pack_requires_run_id_or_case(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["demo-pack", "--output", str(tmp_path / "packet")])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "demo-pack failed: --run-id or --case is required" in captured.err


class _Container:
    def __init__(self, runtime):
        self._runtime = runtime

    def build_persisted_research_agent_runtime(self):
        return self._runtime

    def build_run_summary_use_case(self, runtime=None):
        return BuildRunSummary(runtime or self._runtime, _EvidenceRepo())


class _Runtime:
    def __init__(self, run, events, artifacts):
        self._run = run
        self._events = events
        self._artifacts = artifacts

    def get_run(self, scope, run_id):
        return self._run if run_id == "run-1" else None

    def list_events(self, scope, run_id):
        return self._events

    def list_artifacts(self, scope, run_id):
        return self._artifacts


class _EvidenceRepo:
    def list_evidence(self, *, scope=None, run_id=None, document_id=None, limit=20, tenant_id=None):
        return []
