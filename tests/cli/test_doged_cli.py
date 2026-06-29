from __future__ import annotations

import json

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


def test_doged_serve_api_role_starts_uvicorn(monkeypatch):
    calls: list[dict[str, object]] = []

    def fake_run(app: str, *, host: str, port: int, reload: bool):
        calls.append({"app": app, "host": host, "port": port, "reload": reload})

    monkeypatch.setattr("uvicorn.run", fake_run)
    reset_settings()

    try:
        doged_main.main(["serve", "--role", "api", "--port", "9014"])
    finally:
        monkeypatch.delenv("DOGE_PROCESS_ROLE", raising=False)
        reset_settings()

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
        monkeypatch.delenv("DOGE_PROCESS_ROLE", raising=False)
        reset_settings()

    assert calls == ["worker"]
