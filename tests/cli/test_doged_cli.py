from __future__ import annotations

import json
import os
import zipfile

import pytest

from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType, RunStatus
from doge.config import reset_settings
from doge.interfaces.daemon import main as doged_main


class _ReadyResponse:
    def raise_for_status(self) -> None:
        return None


class _ReadinessResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def _clear_doged_cli_env() -> None:
    os.environ.pop("DOGE_PROCESS_ROLE", None)
    os.environ.pop("DOGE_BIND_HOST", None)
    reset_settings()


def test_doged_status_uses_configured_daemon_port(monkeypatch, capsys):
    calls: list[str] = []

    def fake_get(url: str, *, timeout: float):
        calls.append(url)
        assert timeout == 2.0
        return _ReadyResponse()

    monkeypatch.setenv("DOGE_DAEMON_PORT", "9012")
    monkeypatch.setattr("httpx.get", fake_get)
    reset_settings()

    try:
        doged_main.main(["status"])
    finally:
        reset_settings()

    assert calls == ["http://127.0.0.1:9012/health/ready"]
    assert capsys.readouterr().out.strip() == "ready"


def test_doged_status_port_argument_overrides_config(monkeypatch):
    calls: list[str] = []

    def fake_get(url: str, *, timeout: float):
        calls.append(url)
        return _ReadyResponse()

    monkeypatch.setenv("DOGE_DAEMON_PORT", "9012")
    monkeypatch.setattr("httpx.get", fake_get)
    reset_settings()

    try:
        doged_main.main(["status", "--port", "9013"])
    finally:
        reset_settings()

    assert calls == ["http://127.0.0.1:9013/health/ready"]


def test_doged_doctor_outputs_readiness_json(monkeypatch, capsys):
    calls: list[str] = []
    payload = {
        "status": "ready",
        "checks": {
            "database": {"ok": True},
            "document_storage": {"ok": True},
        },
    }

    def fake_get(url: str, *, timeout: float):
        calls.append(url)
        assert timeout == 2.0
        return _ReadinessResponse(payload)

    monkeypatch.setattr("httpx.get", fake_get)
    reset_settings()

    try:
        doged_main.main(["doctor", "--port", "9015", "--json"])
    finally:
        reset_settings()

    assert calls == ["http://127.0.0.1:9015/health/ready"]
    assert json.loads(capsys.readouterr().out) == payload


def test_doged_doctor_text_reports_checks(monkeypatch, capsys):
    payload = {
        "status": "ready",
        "checks": {
            "database": {"ok": True},
            "document_storage": {"ok": True},
        },
    }

    monkeypatch.setattr("httpx.get", lambda _url, *, timeout: _ReadinessResponse(payload))

    doged_main.main(["doctor"])

    out = capsys.readouterr().out
    assert "status=ready" in out
    assert "database=ok" in out
    assert "document_storage=ok" in out


def test_doged_doctor_verbose_reports_nested_check_details(monkeypatch, capsys):
    payload = {
        "status": "ready",
        "checks": {
            "worker_heartbeat": {
                "ok": True,
                "mode": "in_process",
                "worker_metrics": {"processed": 2, "failed": 0},
            },
        },
    }

    monkeypatch.setattr("httpx.get", lambda _url, *, timeout: _ReadinessResponse(payload))

    doged_main.main(["doctor", "--verbose"])

    out = capsys.readouterr().out
    assert "worker_heartbeat=ok" in out
    assert "  mode=in_process" in out
    assert '  worker_metrics={"failed": 0, "processed": 2}' in out


def test_doged_runs_recent_prints_persisted_runs(monkeypatch, capsys):
    run = AgentRun.create(
        run_id="run-recent",
        workflow="investment_research",
        question="Analyze recent run",
    )
    run.status = RunStatus.COMPLETED
    run.updated_at = "2026-07-05T00:00:00+00:00"
    monkeypatch.setattr(doged_main, "_recent_runs", lambda *, limit: [run])

    doged_main.main(["runs", "--recent", "--limit", "5"])

    out = capsys.readouterr().out
    assert "run_id=run-recent" in out
    assert "status=completed" in out
    assert "workflow=investment_research" in out
    assert "question=Analyze recent run" in out


def test_doged_runs_recent_json(monkeypatch, capsys):
    run = AgentRun.create(run_id="run-json", workflow="earnings_review", question="json")
    monkeypatch.setattr(doged_main, "_recent_runs", lambda *, limit: [run])

    doged_main.main(["runs", "--recent", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["runs"][0]["run_id"] == "run-json"
    assert payload["runs"][0]["workflow"] == "earnings_review"


def test_doged_runs_status_filters_recent_rows(monkeypatch, capsys):
    completed = AgentRun.create(run_id="run-ok", workflow="earnings_review", question="ok")
    completed.status = RunStatus.COMPLETED
    failed = AgentRun.create(run_id="run-failed", workflow="earnings_review", question="failed")
    failed.status = RunStatus.FAILED
    monkeypatch.setattr(doged_main, "_recent_runs", lambda *, limit: [completed, failed])

    doged_main.main(["runs", "--status", "failed"])

    out = capsys.readouterr().out
    assert "run_id=run-failed" in out
    assert "run_id=run-ok" not in out


def test_doged_queue_status_prints_counts(monkeypatch, capsys):
    monkeypatch.setattr(doged_main, "_queue_status", lambda: {"queued": 2, "running": 1})

    doged_main.main(["queue", "--status"])

    out = capsys.readouterr().out.splitlines()
    assert out == ["queued=2", "running=1"]


def test_doged_features_prints_feature_flags(capsys):
    reset_settings()

    doged_main.main(["features"])

    out = capsys.readouterr().out
    assert "run_summary_api=off env=DOGE_FEATURE_RUN_SUMMARY_API" in out
    assert "python_analysis_executor=disabled" in out


def test_doged_routes_prints_registered_routes(monkeypatch, capsys):
    rows = [
        {"methods": ["GET"], "path": "/health/ready", "name": "ready"},
        {"methods": ["POST"], "path": "/v1/sessions", "name": "create_session"},
    ]
    monkeypatch.setattr(doged_main, "_route_rows", lambda: rows)

    doged_main.main(["routes"])

    out = capsys.readouterr().out.splitlines()
    assert out == ["GET /health/ready ready", "POST /v1/sessions create_session"]


def test_doged_explain_prints_failure_point(monkeypatch, capsys):
    run = AgentRun.create(run_id="run-failed", workflow="earnings_review", question="failed")
    run.status = RunStatus.FAILED
    events = [
        AgentEvent(
            event_id="evt-1",
            run_id="run-failed",
            event_type=EventType.ERROR,
            payload={"message": "tool timed out with sk-doged-secret"},
            sequence=7,
        )
    ]
    monkeypatch.setattr(doged_main, "_runtime", lambda: _Runtime(run, events))

    doged_main.main(["explain", "run-failed"])

    out = capsys.readouterr().out
    assert "failure_point=error" in out
    assert "sequence=7" in out
    assert "tool timed out" in out
    assert "sk-doged-secret" not in out
    assert "next_actions=Inspect error,Re-run" in out


def test_doged_explain_missing_run_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(doged_main, "_runtime", lambda: _Runtime(None, []))

    with pytest.raises(SystemExit) as exc:
        doged_main.main(["explain", "run-missing"])

    assert exc.value.code == 1
    assert "explain failed: run not found: run-missing" in capsys.readouterr().err


def test_doged_support_bundle_writes_redacted_zip(tmp_path, monkeypatch, capsys):
    failed = AgentRun.create(run_id="run-failed", workflow="earnings_review", question="failed")
    failed.status = RunStatus.FAILED
    completed = AgentRun.create(run_id="run-ok", workflow="earnings_review", question="ok")
    completed.status = RunStatus.COMPLETED
    monkeypatch.setattr(doged_main, "_fetch_readiness", lambda _port: {"status": "ready", "token": "sk-ready-secret"})
    monkeypatch.setattr(doged_main, "_feature_rows", lambda: [{"name": "run_summary_api", "value": True}])
    monkeypatch.setattr(doged_main, "_route_rows", lambda: [{"methods": ["GET"], "path": "/health/ready", "name": "ready"}])
    monkeypatch.setattr(doged_main, "_queue_status", lambda: {"failed": 1})
    monkeypatch.setattr(doged_main, "_recent_runs", lambda *, limit: [failed, completed])
    monkeypatch.setattr(doged_main, "_config_payload", lambda: {"api_key": "sk-config-secret"})
    monkeypatch.setattr(doged_main, "_version_payload", lambda: {"git_sha": "abc123"})
    output = tmp_path / "support.zip"

    doged_main.main(["support-bundle", "--output", str(output)])

    assert f"support_bundle={output}" in capsys.readouterr().out
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert names == {
            "readiness.json",
            "features.json",
            "routes.json",
            "queue.json",
            "runs_failed.json",
            "config_redacted.json",
            "version.json",
        }
        combined = "\n".join(archive.read(name).decode("utf-8") for name in names)
    assert "run-failed" in combined
    assert "run-ok" not in combined
    assert "sk-ready-secret" not in combined
    assert "sk-config-secret" not in combined


class _Runtime:
    def __init__(self, run, events):
        self._run = run
        self._events = events

    def get_run(self, scope, run_id):
        return self._run if self._run is not None and self._run.run_id == run_id else None

    def list_events(self, scope, run_id):
        return self._events


def test_doged_serve_api_role_starts_uvicorn(monkeypatch):
    calls: list[dict[str, object]] = []

    def fake_run(app: str, *, host: str, port: int, reload: bool):
        calls.append({"app": app, "host": host, "port": port, "reload": reload})

    monkeypatch.setattr("uvicorn.run", fake_run)
    reset_settings()

    try:
        doged_main.main(["serve", "--role", "api", "--port", "9014"])
    finally:
        _clear_doged_cli_env()

    assert calls == [{
        "app": "doge.interfaces.api.main:app",
        "host": "127.0.0.1",
        "port": 9014,
        "reload": False,
    }]


def test_doged_serve_worker_role_runs_worker_process(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(doged_main, "_run_worker_process", lambda: calls.append("worker"))
    reset_settings()

    try:
        doged_main.main(["serve", "--role", "worker"])
    finally:
        _clear_doged_cli_env()

    assert calls == ["worker"]


def test_doged_serve_host_argument_passes_loopback_host_to_uvicorn(monkeypatch):
    calls: list[dict[str, object]] = []

    def fake_run(app: str, *, host: str, port: int, reload: bool):
        calls.append({"app": app, "host": host, "port": port, "reload": reload})

    monkeypatch.setattr("uvicorn.run", fake_run)
    reset_settings()

    try:
        doged_main.main(["serve", "--role", "api", "--host", "127.0.0.1", "--port", "9016"])
    finally:
        _clear_doged_cli_env()

    assert calls == [{
        "app": "doge.interfaces.api.main:app",
        "host": "127.0.0.1",
        "port": 9016,
        "reload": False,
    }]


def test_doged_serve_host_localhost_alias_accepted(monkeypatch):
    hosts: list[str] = []

    def fake_run(app: str, *, host: str, port: int, reload: bool):
        hosts.append(host)

    monkeypatch.setattr("uvicorn.run", fake_run)
    reset_settings()

    try:
        doged_main.main(["serve", "--role", "api", "--host", "localhost", "--port", "9017"])
    finally:
        _clear_doged_cli_env()

    assert hosts == ["localhost"]


def test_doged_serve_host_non_loopback_without_remote_bind_rejected(monkeypatch):
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: None)
    reset_settings()

    try:
        with pytest.raises(AssertionError):
            doged_main.main(["serve", "--role", "api", "--host", "0.0.0.0", "--port", "9018"])
    finally:
        _clear_doged_cli_env()
