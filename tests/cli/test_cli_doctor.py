from __future__ import annotations

import json

from doge.config import reset_settings
from doge.interfaces.cli.commands.doctor import build_local_diagnostics, cmd_doctor


class _Args:
    json = True


def test_cli_doctor_reports_local_checks(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DOGE_DB_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DOGE_AGENT_DB", str(tmp_path / "data" / "agent_state.db"))
    monkeypatch.setenv("DOGE_DOCUMENT_STORAGE_DIR", str(tmp_path / "documents"))
    reset_settings()

    try:
        cmd_doctor(_Args())
    finally:
        reset_settings()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["checks"]["tracked_views_sql"]["ok"] is True
    assert payload["checks"]["agent_database"]["ok"] is True
    assert payload["checks"]["document_storage"]["ok"] is True


def test_build_local_diagnostics_marks_model_provider_noncritical(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGE_DB_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DOGE_TEXT_LLM_PROVIDER", "kimi")
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    reset_settings()

    try:
        payload = build_local_diagnostics()
    finally:
        reset_settings()

    assert payload["status"] == "ok"
    assert payload["checks"]["model_provider_configuration"] == {
        "ok": True,
        "provider": "kimi",
        "configured": False,
        "status": "unconfigured",
    }
