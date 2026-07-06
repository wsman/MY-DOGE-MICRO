"""doged daemon CLI."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import fields
import json
import os
import sys

from doge.config import get_settings, reset_settings
from doge.config.settings import FEATURE_LIFECYCLES


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
    runs.add_argument("--recent", action="store_true", help="show recent runs")
    runs.add_argument("--limit", type=int, default=10)
    runs.add_argument("--json", action="store_true")
    queue = sub.add_parser("queue", help="inspect durable run queue")
    queue.add_argument("--status", action="store_true", help="show queue status counts")
    queue.add_argument("--json", action="store_true")
    features = sub.add_parser("features", help="show configured feature flags")
    features.add_argument("--json", action="store_true")
    routes = sub.add_parser("routes", help="list registered API routes")
    routes.add_argument("--json", action="store_true")
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
