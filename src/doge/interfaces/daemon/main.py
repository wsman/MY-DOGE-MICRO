"""doged daemon CLI."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from doge.config import get_settings, reset_settings


_PROCESS_ROLES = ("api", "worker", "all")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doged", description="MY-DOGE daemon gateway")
    sub = parser.add_subparsers(dest="cmd")
    serve = sub.add_parser("serve", help="start the loopback daemon")
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--reload", action="store_true")
    serve.add_argument("--role", choices=_PROCESS_ROLES, default=None)
    status = sub.add_parser("status", help="check daemon health")
    status.add_argument("--port", type=int, default=None)
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
        if get_settings().daemon.process_role == "worker":
            _run_worker_process()
            return
        _run_api_server(args.port, args.reload)
        return
    if args.cmd == "status":
        import httpx

        port = args.port if args.port is not None else get_settings().daemon.port
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/health/ready", timeout=2.0)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - CLI status path
            print(f"not ready: {exc}", file=sys.stderr)
            sys.exit(1)
            return
        print("ready")


def main_api(argv: list[str] | None = None) -> None:
    main(["serve", "--role", "api", *(argv or [])])


def main_worker(argv: list[str] | None = None) -> None:
    main(["serve", "--role", "worker", *(argv or [])])


def _set_process_role(role: str) -> None:
    os.environ["DOGE_PROCESS_ROLE"] = role
    reset_settings()


def _run_api_server(port: int | None, reload: bool) -> None:
    from doge.interfaces.api.main import _resolve_bind_host
    import uvicorn

    resolved_port = port if port is not None else get_settings().daemon.port
    uvicorn.run("doge.interfaces.api.main:app", host=_resolve_bind_host(), port=resolved_port, reload=reload)


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
