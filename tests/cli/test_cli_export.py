import json

import pytest

from doge.application.use_cases.run_summary import BuildRunSummary
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun, EventType, RunStatus
from doge.interfaces.cli.main import main


def test_cli_export_outputs_redacted_json(capsys, monkeypatch):
    import doge.interfaces.cli.commands.export as export_command

    runtime = _Runtime(_run(), [_event()], [_artifact(secret=True)])
    monkeypatch.setattr(export_command, "_runtime_container", lambda: _Container(runtime))

    main(["export", "run-1", "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["run_id"] == "run-1"
    assert payload["claims"][0]["claim_text"] == "Revenue quality improved"
    assert "REDACTED" in payload["citations"][0]["snippet"]
    assert "sk-export-secret" not in json.dumps(payload)


def test_cli_export_outputs_markdown(capsys, monkeypatch):
    import doge.interfaces.cli.commands.export as export_command

    runtime = _Runtime(_run(), [_event()], [_artifact(secret=True)])
    monkeypatch.setattr(export_command, "_runtime_container", lambda: _Container(runtime))

    main(["export", "run-1", "--format", "md"])

    out = capsys.readouterr().out
    assert out.startswith("# Investment Memo")
    assert "Memo body" in out
    assert "## Claims" in out
    assert "Revenue quality improved" in out
    assert "## Citations" in out
    assert "REDACTED" in out
    assert "sk-export-secret" not in out


def test_cli_export_citations_only_omits_body(capsys, monkeypatch):
    import doge.interfaces.cli.commands.export as export_command

    runtime = _Runtime(_run(), [_event()], [_artifact(secret=True)])
    monkeypatch.setattr(export_command, "_runtime_container", lambda: _Container(runtime))

    main(["export", "run-1", "--citations-only"])

    out = capsys.readouterr().out
    assert out.startswith("## Citations")
    assert "Memo body" not in out
    assert "REDACTED" in out
    assert "sk-export-secret" not in out


def test_cli_export_output_writes_file(tmp_path, capsys, monkeypatch):
    import doge.interfaces.cli.commands.export as export_command

    runtime = _Runtime(_run(), [_event()], [_artifact()])
    monkeypatch.setattr(export_command, "_runtime_container", lambda: _Container(runtime))
    output = tmp_path / "memo.md"

    main(["export", "run-1", "--output", str(output)])

    assert capsys.readouterr().out == ""
    assert output.read_text(encoding="utf-8").startswith("# Investment Memo")


def test_cli_export_missing_run_exits_1(capsys, monkeypatch):
    import doge.interfaces.cli.commands.export as export_command

    runtime = _Runtime(None, [], [])
    monkeypatch.setattr(export_command, "_runtime_container", lambda: _Container(runtime))

    with pytest.raises(SystemExit) as exc:
        main(["export", "run-missing"])

    assert exc.value.code == 1
    assert "export failed: run not found: run-missing" in capsys.readouterr().err


def test_cli_export_requires_run_id():
    with pytest.raises(SystemExit) as exc:
        main(["export"])

    assert exc.value.code == 2


def _run():
    run = AgentRun.create(workflow="investment_research", question="Analyze", run_id="run-1")
    run.status = RunStatus.COMPLETED
    return run


def _artifact(*, secret: bool = False):
    snippet = "sk-export-secret" if secret else "annual report p.4"
    return AgentArtifact(
        artifact_id="art-1",
        run_id="run-1",
        kind="investment_memo",
        title="Memo",
        content="Memo body",
        data={
            "claims": [{"text": "Revenue quality improved", "status": "supported"}],
            "citations": [{
                "citation_id": "cit-1",
                "source": "annual-report.pdf",
                "document_id": "doc-1",
                "page_number": 4,
                "snippet": snippet,
            }],
        },
    )


def _event():
    return AgentEvent("evt-1", "run-1", EventType.RUN_CREATED, sequence=1)


class _Container:
    def __init__(self, runtime):
        self._runtime = runtime

    def build_persisted_research_agent_runtime(self):
        return self._runtime

    def build_run_summary_use_case(self, runtime=None):
        return BuildRunSummary(runtime or self._runtime)


class _Runtime:
    def __init__(self, run, events, artifacts):
        self._run = run
        self._events = events
        self._artifacts = artifacts

    def get_run(self, scope, run_id):
        return self._run if self._run is not None and run_id == "run-1" else None

    def list_events(self, scope, run_id):
        return self._events

    def list_artifacts(self, scope, run_id):
        return self._artifacts
