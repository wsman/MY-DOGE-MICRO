"""doged daemon CLI."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import fields
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from doge.config import get_settings, reset_settings
from doge.config.settings import FEATURE_LIFECYCLES
from doge.core.security import redact_secrets
from doge.interfaces.cli.run_status_labels import next_actions_for_run_status


_PROCESS_ROLES = ("api", "worker", "all")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doged", description="MY-DOGE daemon gateway")
    sub = parser.add_subparsers(dest="cmd")
    serve = sub.add_parser("serve", help="start the loopback daemon")
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--reload", action="store_true")
    serve.add_argument("--role", choices=_PROCESS_ROLES, default=None)
    serve.add_argument("--host", default=None, help="loopback bind host (overrides DOGE_BIND_HOST)")
    status = sub.add_parser("status", help="check daemon health")
    status.add_argument("--port", type=int, default=None)
    doctor = sub.add_parser("doctor", help="show daemon readiness checks")
    doctor.add_argument("--port", type=int, default=None)
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--verbose", action="store_true", help="show nested readiness details")
    runs = sub.add_parser("runs", help="inspect recent persisted runs")
    runs.add_argument("--recent", action="store_true", help="canonical selector for recent persisted runs")
    runs.add_argument("--limit", type=int, default=10)
    runs.add_argument("--status", help="filter recent runs by status")
    runs.add_argument("--json", action="store_true")
    queue = sub.add_parser("queue", help="inspect durable run queue")
    queue.add_argument("--status", action="store_true", help="canonical selector for queue status counts")
    queue.add_argument("--json", action="store_true")
    features = sub.add_parser("features", help="show configured feature flags")
    features.add_argument("--json", action="store_true")
    routes = sub.add_parser("routes", help="list registered API routes")
    routes.add_argument("--json", action="store_true")
    slots = sub.add_parser("slots", help="list registered platform slots")
    slots.add_argument("--json", action="store_true")
    explain = sub.add_parser("explain", help="explain a failed or terminal run")
    explain.add_argument("run_id")
    support = sub.add_parser("support-bundle", help="write a redacted operator support bundle")
    support.add_argument("--output", required=True, help="zip file path")
    support.add_argument("--limit", type=int, default=50, help="failed-runs lookup window")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return
    if args.cmd == "serve":
        if args.role is not None:
            _set_process_role(args.role)
        if args.host is not None:
            _set_bind_host(args.host)
        if get_settings().daemon.process_role == "worker":
            _run_worker_process()
            return
        _run_api_server(args.port, args.reload)
        return
    if args.cmd == "status":
        try:
            _fetch_readiness(args.port)
        except Exception as exc:  # noqa: BLE001 - CLI status path
            print(f"not ready: {exc}", file=sys.stderr)
            sys.exit(1)
            return
        print("ready")
        return
    if args.cmd == "doctor":
        try:
            payload = _fetch_readiness(args.port)
        except Exception as exc:  # noqa: BLE001 - CLI doctor path
            payload = {
                "status": "not_ready",
                "checks": {
                    "daemon_http": {
                        "ok": False,
                        "message": str(exc),
                    }
                },
            }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            _print_readiness(payload, verbose=args.verbose)
        if payload.get("status") != "ready":
            sys.exit(1)
        return
    if args.cmd == "runs":
        rows = [_run_summary(run) for run in _recent_runs(limit=args.limit)]
        if args.status:
            rows = [row for row in rows if row["status"] == args.status]
        if args.json:
            print(json.dumps({"runs": rows}, ensure_ascii=False, sort_keys=True))
        else:
            _print_runs(rows)
        return
    if args.cmd == "queue":
        payload = {"queue": _queue_status()}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            _print_queue(payload["queue"])
        return
    if args.cmd == "features":
        rows = _feature_rows()
        if args.json:
            print(json.dumps({"features": rows}, ensure_ascii=False, sort_keys=True))
        else:
            _print_features(rows)
        return
    if args.cmd == "routes":
        rows = _route_rows()
        if args.json:
            print(json.dumps({"routes": rows}, ensure_ascii=False, sort_keys=True))
        else:
            _print_routes(rows)
        return
    if args.cmd == "slots":
        rows = _slot_rows()
        if args.json:
            print(json.dumps({"slots": rows}, ensure_ascii=False, sort_keys=True))
        else:
            _print_slots(rows)
        return
    if args.cmd == "explain":
        _explain_run(args.run_id)
        return
    if args.cmd == "support-bundle":
        output = _write_support_bundle(Path(args.output), limit=args.limit)
        print(f"support_bundle={output}")
        return


def main_api(argv: list[str] | None = None) -> None:
    main(["serve", "--role", "api", *(argv or [])])


def main_worker(argv: list[str] | None = None) -> None:
    main(["serve", "--role", "worker", *(argv or [])])


def _set_process_role(role: str) -> None:
    os.environ["DOGE_PROCESS_ROLE"] = role
    reset_settings()


def _set_bind_host(host: str) -> None:
    """Inject a CLI-supplied bind host through the same env path the API startup gate reads."""
    os.environ["DOGE_BIND_HOST"] = host
    reset_settings()


def _run_api_server(port: int | None, reload: bool) -> None:
    from doge.interfaces.api.main import _resolve_bind_host
    import uvicorn

    resolved_port = port if port is not None else get_settings().daemon.port
    uvicorn.run("doge.interfaces.api.main:app", host=_resolve_bind_host(), port=resolved_port, reload=reload)


def _fetch_readiness(port: int | None) -> dict:
    import httpx

    resolved_port = port if port is not None else get_settings().daemon.port
    response = httpx.get(f"http://127.0.0.1:{resolved_port}/health/ready", timeout=2.0)
    response.raise_for_status()
    try:
        payload = response.json()
    except Exception:
        return {"status": "ready", "checks": {}}
    if not isinstance(payload, dict):
        return {"status": "not_ready", "checks": {"daemon_http": {"ok": False, "message": "invalid payload"}}}
    return payload


def _print_readiness(payload: dict, *, verbose: bool = False) -> None:
    print(f"status={payload.get('status', 'unknown')}")
    checks = payload.get("checks", {})
    if not isinstance(checks, dict):
        return
    for name in sorted(checks):
        check = checks[name] if isinstance(checks[name], dict) else {"ok": False}
        status = "ok" if check.get("ok") else "failed"
        suffix = f": {check['message']}" if check.get("message") else ""
        print(f"{name}={status}{suffix}")
        if verbose:
            for key in sorted(check):
                if key in {"ok", "message"}:
                    continue
                print(f"  {key}={_format_cli_value(check[key])}")


def _recent_runs(*, limit: int):
    from doge.interfaces.api.container import app_container
    from doge.shared.scope import TenantScope

    repositories = app_container.runtime.build_agent_repositories()
    return repositories["runs"].list_recent(TenantScope.local(), limit=limit)


def _queue_status() -> dict[str, int]:
    from doge.interfaces.api.container import app_container

    return app_container.runtime.build_agent_run_queue().status_summary()


def _feature_rows() -> list[dict[str, object]]:
    settings = get_settings()
    rows: list[dict[str, object]] = []
    for field in fields(settings.features):
        name = field.name
        value = getattr(settings.features, name)
        lifecycle = FEATURE_LIFECYCLES.get(name)
        row: dict[str, object] = {
            "name": name,
            "value": value,
        }
        if lifecycle is not None:
            row.update({
                "env_var": lifecycle.env_var,
                "target_default_on": lifecycle.target_default_on,
                "target_removal": lifecycle.target_removal,
            })
        rows.append(row)
    return rows


def _route_rows() -> list[dict[str, object]]:
    from doge.interfaces.api.main import app

    rows: list[dict[str, object]] = []
    for route in app.routes:
        methods = sorted(method for method in getattr(route, "methods", set()) if method not in {"HEAD", "OPTIONS"})
        if not methods:
            continue
        rows.append({
            "path": getattr(route, "path", ""),
            "methods": methods,
            "name": getattr(route, "name", ""),
        })
    return sorted(rows, key=lambda row: (str(row["path"]), ",".join(row["methods"])))


def _slot_rows() -> list[dict[str, object]]:
    from doge.bootstrap.runtime_factories.slots import build_slot_status_rows

    return list(build_slot_status_rows())


def _runtime():
    from doge.bootstrap import build_runtime_container

    return build_runtime_container().build_persisted_research_agent_runtime()


def _explain_run(run_id: str) -> None:
    from doge.core.domain.agent_models import EventType
    from doge.shared.scope import TenantScope

    runtime = _runtime()
    scope = TenantScope.local()
    run = runtime.get_run(scope, run_id)
    if run is None:
        print(f"explain failed: run not found: {run_id}", file=sys.stderr)
        sys.exit(1)
        return
    events = runtime.list_events(scope, run_id)
    error_event = next((event for event in reversed(events) if event.event_type == EventType.ERROR), None)
    if error_event is None:
        print("failure_point=none")
        print(f"status={_status_value(run.status)}")
    else:
        payload = getattr(error_event, "payload", {}) or {}
        print("failure_point=error")
        print(f"sequence={getattr(error_event, 'sequence', 0)}")
        print(f"message={_safe_message(payload)}")
    print("next_actions=" + ",".join(next_actions_for_run_status(_status_value(run.status))))


def _write_support_bundle(output: Path, *, limit: int) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    failed_runs = [
        _run_summary(run)
        for run in _recent_runs(limit=limit)
        if _status_value(run.status) == "failed"
    ]
    payloads = {
        "readiness.json": _readiness_payload(),
        "features.json": {"features": _feature_rows()},
        "routes.json": {"routes": _route_rows()},
        "queue.json": {"queue": _queue_status()},
        "runs_failed.json": {"runs": failed_runs},
        "config_redacted.json": _config_payload(),
        "version.json": _version_payload(),
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in payloads.items():
            archive.writestr(
                name,
                json.dumps(redact_secrets(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
    return output


def _readiness_payload() -> dict[str, object]:
    try:
        return _fetch_readiness(None)
    except Exception as exc:  # noqa: BLE001 - support bundle records readiness failure safely
        return {"status": "not_ready", "error": str(exc)}


def _config_payload() -> dict[str, object]:
    settings = get_settings()
    payload: dict[str, object] = {"settings_class": type(settings).__name__}
    for field in fields(settings):
        name = field.name
        value = getattr(settings, name)
        if hasattr(value, "__dict__"):
            payload[name] = {
                key: _json_safe(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        else:
            payload[name] = _json_safe(value)
    return payload


def _version_payload() -> dict[str, object]:
    return {
        "package": "my-doge-micro",
        "git_sha": _git_sha(),
    }


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _safe_message(payload: dict[str, object]) -> str:
    candidate = payload.get("message") or payload.get("error") or payload.get("detail") or ""
    if isinstance(candidate, dict):
        candidate = candidate.get("message") or candidate.get("public_message") or json.dumps(candidate, sort_keys=True)
    return str(redact_secrets(candidate))


def _json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _run_summary(run) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "status": _status_value(run.status),
        "workflow": run.workflow,
        "question": run.question,
        "market": run.market,
        "session_id": run.session_id,
        "updated_at": run.updated_at,
        "created_at": run.created_at,
    }


def _print_runs(rows: list[dict[str, object]]) -> None:
    if not rows:
        print("no recent runs")
        return
    for row in rows:
        print(
            " ".join([
                f"run_id={row['run_id']}",
                f"status={row['status']}",
                f"workflow={row['workflow']}",
                f"updated_at={row['updated_at']}",
                f"question={_compact(row['question'])}",
            ])
        )


def _print_queue(counts: dict[str, int]) -> None:
    if not counts:
        print("queue=empty")
        return
    for status in sorted(counts):
        print(f"{status}={counts[status]}")


def _print_features(rows: list[dict[str, object]]) -> None:
    for row in rows:
        value = row["value"]
        if isinstance(value, bool):
            rendered = "on" if value else "off"
        else:
            rendered = str(value)
        suffix = f" env={row['env_var']}" if row.get("env_var") else ""
        print(f"{row['name']}={rendered}{suffix}")


def _print_routes(rows: list[dict[str, object]]) -> None:
    for row in rows:
        print(f"{','.join(row['methods'])} {row['path']} {row['name']}")


def _print_slots(rows: list[dict[str, object]]) -> None:
    for row in rows:
        flags = ",".join(row["feature_flags"]) if row.get("feature_flags") else "-"
        counts = row.get("counts", {})
        tools = counts.get("tools", 0) if isinstance(counts, dict) else 0
        health = row.get("health", {})
        health_status = health.get("status", "unknown") if isinstance(health, dict) else "unknown"
        print(
            " ".join([
                f"{row['id']}",
                f"status={row['status']}",
                f"type={row['type']}",
                f"health={health_status}",
                f"tools={tools}",
                f"flags={flags}",
            ])
        )


def _format_cli_value(value) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _status_value(status) -> str:
    return getattr(status, "value", str(status))


def _compact(value, *, limit: int = 80) -> str:
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= limit else f"{text[:limit - 3]}..."


def _run_worker_process() -> None:
    try:
        asyncio.run(_run_worker_until_stopped())
    except KeyboardInterrupt:
        return


async def _run_worker_until_stopped() -> None:
    from doge.interfaces.api import deps

    settings = get_settings()
    worker = deps.get_daemon_worker()
    outbox_publisher = None
    if settings.features.runtime_outbox_publisher:
        outbox_publisher = deps.get_runtime_outbox_publisher()
        outbox_publisher.start()
    worker.start()
    try:
        await asyncio.Event().wait()
    finally:
        await worker.stop()
        if outbox_publisher is not None:
            await outbox_publisher.stop()


if __name__ == "__main__":
    main()
