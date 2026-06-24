"""SQLite-backed daemon readiness checks."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from doge.config import Settings, get_settings
from doge.infrastructure.database.migration_runner import registered_migrations


class SQLiteRuntimeReadinessProbe:
    """Collect readiness details for the local SQLite daemon topology."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        db_path: Path | str | None = None,
        document_storage_dir: Path | str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._db_path = Path(db_path) if db_path is not None else self._settings.db.agent_db
        self._document_storage_dir = (
            Path(document_storage_dir)
            if document_storage_dir is not None
            else self._settings.documents.storage_dir
        )

    def snapshot(self, *, process_role: str, worker: Any = None) -> dict[str, Any]:
        checks = {
            "database": self._database_check(),
            "migration_version": self._migration_check(),
            "queue_depth": self._queue_depth_check(),
            "worker_heartbeat": self._worker_check(process_role, worker),
            "outbox_backlog": self._outbox_backlog_check(),
            "document_storage": self._document_storage_check(),
            "model_provider_configuration": self._model_provider_check(),
        }
        critical = {"database", "migration_version", "queue_depth", "document_storage"}
        if process_role in {"all", "worker"}:
            critical.add("worker_heartbeat")
        ready = all(bool(checks[name]["ok"]) for name in critical)
        return {
            "status": "ready" if ready else "not_ready",
            "process_role": process_role,
            "checks": checks,
        }

    def _database_check(self) -> dict[str, Any]:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1").fetchone()
        except Exception as exc:  # noqa: BLE001 - readiness reports sanitized status
            return {"ok": False, "message": type(exc).__name__}
        return {"ok": True}

    def _migration_check(self) -> dict[str, Any]:
        expected = {migration.key for migration in registered_migrations()}
        try:
            with self._connect() as conn:
                rows = conn.execute("SELECT name FROM schema_migrations").fetchall()
        except Exception as exc:  # noqa: BLE001 - readiness reports sanitized status
            return {
                "ok": False,
                "expected": len(expected),
                "applied": 0,
                "missing": sorted(expected),
                "message": type(exc).__name__,
            }
        applied = {str(row["name"]) for row in rows}
        missing = sorted(expected - applied)
        return {
            "ok": not missing,
            "expected": len(expected),
            "applied": len(applied),
            "missing": missing,
        }

    def _queue_depth_check(self) -> dict[str, Any]:
        try:
            counts = self._latest_status_counts("run_queue", "run_id", "queue_id")
        except Exception as exc:  # noqa: BLE001 - readiness reports sanitized status
            return {"ok": False, "message": type(exc).__name__}
        return {
            "ok": True,
            "queued": counts.get("queued", 0),
            "running": counts.get("running", 0),
            "done": counts.get("done", 0),
            "failed": counts.get("failed", 0),
            "cancelled": counts.get("cancelled", 0),
        }

    def _worker_check(self, process_role: str, worker: Any = None) -> dict[str, Any]:
        latest = self._latest_worker_heartbeat()
        if process_role == "api":
            return {"ok": True, "mode": "external", "latest_heartbeat": latest}
        running = bool(getattr(worker, "is_running", lambda: False)()) if worker is not None else False
        return {
            "ok": running,
            "mode": "in_process",
            "worker_id": getattr(worker, "worker_id", None) if worker is not None else None,
            "loop_running": running,
            "latest_heartbeat": latest,
        }

    def _outbox_backlog_check(self) -> dict[str, Any]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT status, COUNT(*) AS count
                    FROM runtime_outbox
                    GROUP BY status
                    """
                ).fetchall()
        except Exception as exc:  # noqa: BLE001 - readiness reports sanitized status
            return {"ok": False, "message": type(exc).__name__}
        counts = {str(row["status"]): int(row["count"]) for row in rows}
        return {
            "ok": True,
            "pending": counts.get("pending", 0),
            "leased": counts.get("leased", 0),
            "published": counts.get("published", 0),
        }

    def _document_storage_check(self) -> dict[str, Any]:
        try:
            self._document_storage_dir.mkdir(parents=True, exist_ok=True)
            ok = self._document_storage_dir.is_dir() and os.access(self._document_storage_dir, os.W_OK)
        except Exception as exc:  # noqa: BLE001 - readiness reports sanitized status
            return {"ok": False, "message": type(exc).__name__}
        return {"ok": bool(ok)}

    def _model_provider_check(self) -> dict[str, Any]:
        provider = self._settings.llm.text_provider.lower()
        configured = True
        if provider == "kimi":
            configured = bool(self._settings.kimi.api_key)
        elif provider == "deepseek":
            configured = bool(self._settings.deepseek.api_key)
        return {
            "ok": True,
            "provider": provider,
            "configured": configured,
            "status": "configured" if configured else "unconfigured",
        }

    def _latest_status_counts(self, table: str, entity_column: str, order_column: str) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT latest.status, COUNT(*) AS count
                FROM {table} latest
                JOIN (
                    SELECT {entity_column}, MAX({order_column}) AS max_order
                    FROM {table}
                    GROUP BY {entity_column}
                ) grouped
                ON latest.{entity_column} = grouped.{entity_column}
                AND latest.{order_column} = grouped.max_order
                GROUP BY latest.status
                """
            ).fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}

    def _latest_worker_heartbeat(self) -> dict[str, Any] | None:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT worker_id, updated_at, lease_expires_at
                    FROM run_queue
                    WHERE status = 'running'
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ).fetchone()
        except Exception:
            return None
        if row is None:
            return None
        return {
            "worker_id": row["worker_id"],
            "updated_at": row["updated_at"],
            "lease_expires_at": row["lease_expires_at"],
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
