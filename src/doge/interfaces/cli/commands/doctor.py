"""CLI command: doctor."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from doge.config import get_settings
from doge.infrastructure.database.readiness import sqlite_access_check


def cmd_doctor(args) -> None:
    """Run local diagnostics for the non-daemon CLI surface.

    ``--next`` (Sprint UX-1 Slice C, CLI-2) adds environment-aware next-step
    guidance: in JSON mode an additive top-level ``guidance[]`` array (existing
    fields unchanged; JSON without ``--next`` is byte-identical), in text mode a
    ``next:`` block per failing check. Exit code is unchanged (1 on not_ready).
    """
    show_next = getattr(args, "next", False)
    report = build_local_diagnostics()
    if getattr(args, "json", False):
        if show_next:
            # Additive only with --next; JSON without it stays byte-identical.
            report["guidance"] = _guidance_for(report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        _print_text_report(report)
        if show_next:
            _print_next_guidance(report)
    if report["status"] != "ok":
        sys.exit(1)


def build_local_diagnostics() -> dict[str, Any]:
    settings = get_settings()
    checks = {
        "config": _ok({
            "project_root": str(settings.project_root),
            "db_dir": str(settings.db.dir),
            "document_storage_dir": str(settings.documents.storage_dir),
        }),
        "database_paths": _database_paths_check(settings),
        "tracked_views_sql": _file_exists_check(settings.db.resolved_views_sql()),
        "agent_database": _sqlite_access_check(settings.db.agent_db),
        "document_storage": _writable_directory_check(settings.documents.storage_dir),
        "model_provider_configuration": _model_provider_check(settings),
    }
    critical = {
        "config",
        "database_paths",
        "tracked_views_sql",
        "agent_database",
        "document_storage",
    }
    status = "ok" if all(checks[name]["ok"] for name in critical) else "not_ready"
    return {
        "status": status,
        "checks": checks,
        "critical_checks": sorted(critical),
    }


def _database_paths_check(settings) -> dict[str, Any]:
    paths = {
        "db_dir": settings.db.dir,
        "cn_db": settings.db.cn_db,
        "us_db": settings.db.us_db,
        "research_db": settings.db.research_db,
        "agent_db": settings.db.agent_db,
        "duckdb": settings.db.duckdb,
    }
    details: dict[str, Any] = {name: str(path) for name, path in paths.items()}
    try:
        settings.db.dir.mkdir(parents=True, exist_ok=True)
        writable = _is_writable_dir(settings.db.dir)
        parents_ok = all(_ensure_parent(path) for name, path in paths.items() if name != "db_dir")
    except Exception as exc:  # noqa: BLE001 - diagnostics report sanitized status
        return _fail(type(exc).__name__, details)
    return {"ok": bool(writable and parents_ok), **details}


def _file_exists_check(path: Path) -> dict[str, Any]:
    return {"ok": path.exists() and path.is_file(), "path": str(path)}


def _sqlite_access_check(path: Path) -> dict[str, Any]:
    try:
        _ensure_parent(path)
    except Exception as exc:  # noqa: BLE001 - diagnostics report sanitized status
        return _fail(type(exc).__name__, {"path": str(path)})
    return {**sqlite_access_check(path), "path": str(path)}


def _writable_directory_check(path: Path) -> dict[str, Any]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        ok = _is_writable_dir(path)
    except Exception as exc:  # noqa: BLE001 - diagnostics report sanitized status
        return _fail(type(exc).__name__, {"path": str(path)})
    return {"ok": bool(ok), "path": str(path)}


def _model_provider_check(settings) -> dict[str, Any]:
    provider = settings.llm.text_provider.lower()
    configured = True
    if provider == "kimi":
        configured = bool(settings.kimi.api_key)
    elif provider == "deepseek":
        configured = bool(settings.deepseek.api_key)
    return {
        "ok": True,
        "provider": provider,
        "configured": configured,
        "status": "configured" if configured else "unconfigured",
    }


def _ensure_parent(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.parent.is_dir() and _is_writable_dir(path.parent)


def _is_writable_dir(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK)


def _ok(details: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **details}


def _fail(message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "message": message, **details}


def _print_text_report(report: dict[str, Any]) -> None:
    print(f"status={report['status']}")
    checks = report.get("checks", {})
    for name in sorted(checks):
        check = checks[name]
        status = "ok" if check.get("ok") else "failed"
        suffix = f": {check['message']}" if check.get("message") else ""
        print(f"{name}={status}{suffix}")


# Static, per-check next-step guidance for ``doge doctor --next`` (UX-1 Slice C).
# Keys mirror the check names emitted by ``build_local_diagnostics``. A failing
# check with no entry here simply gets no guidance row.
_NEXT_STEPS: dict[str, list[str]] = {
    "config": [
        "Check that the project root and db_dir are writable and not locked by another process."
    ],
    "database_paths": [
        "Ensure the data/ directory exists and the CN/US/research/agent SQLite paths are writable."
    ],
    "tracked_views_sql": [
        "The tracked views SQL file (src/doge/infrastructure/database/views.sql) is missing — restore it from version control or reinstall the package."
    ],
    "agent_database": [
        "Ensure the agent-state SQLite DB parent directory exists and is writable (DOGE_AGENT_DB)."
    ],
    "document_storage": [
        "Ensure the document storage directory exists and is writable (DOGE_DOCUMENT_STORAGE_DIR)."
    ],
    "model_provider_configuration": [
        "Set MOONSHOT_API_KEY (Kimi) or DEEPSEEK_API_KEY to enable a live model; otherwise the deterministic scripted fallback is used."
    ],
}


def _guidance_for(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the additive ``guidance[]`` block: one entry per failing check that
    has a known next-step, each carrying its static ``next_steps`` list."""
    guidance: list[dict[str, Any]] = []
    for name, check in report.get("checks", {}).items():
        if check.get("ok") or name not in _NEXT_STEPS:
            continue
        guidance.append({"check": name, "next_steps": list(_NEXT_STEPS[name])})
    return guidance


def _print_next_guidance(report: dict[str, Any]) -> None:
    """Print a ``next:`` block per failing check (text mode, ``--next`` only)."""
    guidance = _guidance_for(report)
    if not guidance:
        return
    print("next:")
    for entry in guidance:
        print(f"  {entry['check']}:")
        for step in entry["next_steps"]:
            print(f"    - {step}")
