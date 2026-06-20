"""doged daemon CLI."""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doged", description="MY-DOGE daemon gateway")
    sub = parser.add_subparsers(dest="cmd")
    serve = sub.add_parser("serve", help="start the loopback daemon")
    serve.add_argument("--port", type=int, default=8901)
    serve.add_argument("--reload", action="store_true")
    sub.add_parser("status", help="check daemon health")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return
    if args.cmd == "serve":
        from doge.interfaces.api.main import _resolve_bind_host
        import uvicorn

        uvicorn.run("doge.interfaces.api.main:app", host=_resolve_bind_host(), port=args.port, reload=args.reload)
        return
    if args.cmd == "status":
        import httpx

        try:
            response = httpx.get("http://127.0.0.1:8901/health/ready", timeout=2.0)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - CLI status path
            print(f"not ready: {exc}", file=sys.stderr)
            sys.exit(1)
            return
        print("ready")


if __name__ == "__main__":
    main()
