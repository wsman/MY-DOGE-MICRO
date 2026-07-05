from __future__ import annotations

import json

import pytest

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


def test_cli_doctor_next_adds_guidance_for_failing_checks(monkeypatch, capsys):
    # ``--next`` adds an additive top-level ``guidance[]`` with one entry per
    # failing check that has a known next-step. The report is monkeypatched so
    # the test does not depend on local filesystem state.
    from doge.interfaces.cli.commands import doctor as doctor_mod

    fake_report = {
        "status": "not_ready",
        "checks": {
            "tracked_views_sql": {"ok": False, "path": "/missing/views.sql"},
            "model_provider_configuration": {
                "ok": True,
                "provider": "kimi",
                "configured": False,
                "status": "unconfigured",
            },
        },
        "critical_checks": ["tracked_views_sql"],
    }
    monkeypatch.setattr(doctor_mod, "build_local_diagnostics", lambda: fake_report)

    class _ArgsNext:
        json = True
        next = True

    with pytest.raises(SystemExit) as exc:
        doctor_mod.cmd_doctor(_ArgsNext())
    assert exc.value.code == 1  # not_ready -> exit 1 (unchanged)

    payload = json.loads(capsys.readouterr().out)
    guided = {entry["check"] for entry in payload["guidance"]}
    assert "tracked_views_sql" in guided               # failing -> guided
    assert "model_provider_configuration" not in guided  # ok=True -> excluded
    for entry in payload["guidance"]:
        assert entry["next_steps"]
        assert all(isinstance(s, str) for s in entry["next_steps"])


def test_cli_doctor_json_without_next_is_byte_identical_to_pre_slice_c(monkeypatch, capsys):
    # No `next` attr -> no guidance key; the JSON shape is unchanged.
    from doge.interfaces.cli.commands import doctor as doctor_mod

    fake_report = {
        "status": "not_ready",
        "checks": {"tracked_views_sql": {"ok": False, "path": "/missing"}},
        "critical_checks": ["tracked_views_sql"],
    }
    monkeypatch.setattr(doctor_mod, "build_local_diagnostics", lambda: fake_report)

    class _ArgsJsonOnly:
        json = True

    with pytest.raises(SystemExit):
        doctor_mod.cmd_doctor(_ArgsJsonOnly())

    payload = json.loads(capsys.readouterr().out)
    assert "guidance" not in payload
    assert set(payload.keys()) == {"status", "checks", "critical_checks"}


def test_cli_doctor_next_text_prints_next_block(monkeypatch, capsys):
    from doge.interfaces.cli.commands import doctor as doctor_mod

    fake_report = {
        "status": "not_ready",
        "checks": {"tracked_views_sql": {"ok": False, "path": "/missing"}},
        "critical_checks": ["tracked_views_sql"],
    }
    monkeypatch.setattr(doctor_mod, "build_local_diagnostics", lambda: fake_report)

    class _ArgsTextNext:
        json = False
        next = True

    with pytest.raises(SystemExit):
        doctor_mod.cmd_doctor(_ArgsTextNext())

    out = capsys.readouterr().out
    assert "tracked_views_sql=failed" in out
    assert "next:" in out
    assert "tracked_views_sql:" in out
