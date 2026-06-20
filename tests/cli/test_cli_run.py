import json

from doge.config import reset_settings
from doge.interfaces.cli.main import main


def test_cli_run_json_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()

    main(["run", "Analyze earnings quality", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["run_id"].startswith("run-")
    assert payload["status"] == "awaiting_approval"


def test_cli_run_trace_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "agent_state.db"))
    reset_settings()

    main(["run", "Analyze earnings quality", "--trace"])

    out = capsys.readouterr().out
    assert "run_id=run-" in out
    assert "tool_call" in out
