from __future__ import annotations

import json
import os

import pytest

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
