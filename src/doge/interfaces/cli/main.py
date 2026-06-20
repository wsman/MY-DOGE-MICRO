"""Canonical CLI entrypoint for MY-DOGE-MICRO.

Usage:
    doge stock <ticker> [--market cn] [--days 20]
    doge rsrs [--market cn] [--top 20]
    doge breadth [--market cn] [--days 10]
    doge anomaly [--min-ratio 3.0] [--top 20]
    doge demo [--market cn] [--top 5]
    doge macro [--verbose]
    doge session [--title "..."]
    doge run "question" [--session <session_id>] [--json] [--trace]

Clean-architecture wiring (ADR-0001 / ADR-0010): each subcommand delegates to
its read-only service or application use case via ``doge.application.composition``.
This file contains NO inline SQL and opens NO DuckDB/SQLite connections directly.

Exit codes:
    0  success (including help when no subcommand is given)
    1  query returned no rows / macro failed
    2  argparse rejection (invalid flag / value)
"""

import argparse
import sys

# Force UTF-8 stdout on Windows (and any platform where the terminal uses a
# narrow encoding) so emoji/Chinese output never raises UnicodeEncodeError.
# This is a process-wide guard; individual commands may also use _safe_print.
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name)
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from doge.interfaces.cli.commands import (
    cmd_anomaly,
    cmd_breadth,
    cmd_demo,
    cmd_macro,
    cmd_run,
    cmd_rsrs,
    cmd_session,
    cmd_stock,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argparse parser and subparsers."""
    parser = argparse.ArgumentParser(
        prog="doge",
        description="MY-DOGE stock data query tool",
    )
    sub = parser.add_subparsers(dest="cmd")

    # stock
    p_stock = sub.add_parser("stock", help="query stock price and indicators")
    p_stock.add_argument("ticker", help="ticker symbol (e.g. 301599.SZ, AAPL)")
    p_stock.add_argument("--market", default="cn", choices=["cn", "us"])
    p_stock.add_argument("--days", type=int, default=20)

    # rsrs
    p_rsrs = sub.add_parser("rsrs", help="RSRS momentum ranking")
    p_rsrs.add_argument("--market", default="cn", choices=["cn", "us"])
    p_rsrs.add_argument("--top", type=int, default=20)

    # breadth
    p_breadth = sub.add_parser("breadth", help="market breadth (advancers/decliners)")
    p_breadth.add_argument("--market", default="cn", choices=["cn", "us"])
    p_breadth.add_argument("--days", type=int, default=10)

    # anomaly
    p_anomaly = sub.add_parser("anomaly", help="volume anomaly detection")
    p_anomaly.add_argument("--min-ratio", type=float, default=3.0)
    p_anomaly.add_argument("--top", type=int, default=20)

    # demo
    p_demo = sub.add_parser("demo", help="5-minute demo using bundled sample data")
    p_demo.add_argument("--market", default="cn", choices=["cn", "us"])
    p_demo.add_argument("--top", type=int, default=5)

    # macro
    p_macro = sub.add_parser("macro", help="macro strategy report via configured text LLM")
    p_macro.add_argument("--market", default="cn", choices=["cn", "us"])
    p_macro.add_argument("--verbose", action="store_true", help="verbose output")
    p_macro.add_argument("--config-file", help="ignored — accepted for forward compatibility")

    # session
    p_session = sub.add_parser("session", help="create or resume an agent session")
    p_session.add_argument("--title", default="Research session")
    p_session.add_argument("--resume", help="session id to resume")
    p_session.add_argument("--message", help="execute one message in the resumed session")
    p_session.add_argument("--market", default="us", choices=["cn", "us"])
    p_session.add_argument("--list", action="store_true", help="list recent sessions")
    p_session.add_argument("--limit", type=int, default=20)
    p_session.add_argument("--interactive", action="store_true", help="enter an interactive session loop")

    # run
    p_run = sub.add_parser("run", help="execute a persisted research-agent run")
    p_run.add_argument("question", help="research question")
    p_run.add_argument("--session", help="attach the run to an existing session")
    p_run.add_argument("--market", default="us", choices=["cn", "us"])
    p_run.add_argument("--language", default="en")
    p_run.add_argument("--portfolio", default="portfolio-demo")
    p_run.add_argument("--max-tool-rounds", type=int, default=8)
    p_run.add_argument("--json", action="store_true", help="emit JSON only")
    p_run.add_argument("--trace", action="store_true", help="print event trace after the summary")

    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse argv and dispatch to the matching command handler."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return

    dispatch = {
        "stock": cmd_stock,
        "rsrs": cmd_rsrs,
        "breadth": cmd_breadth,
        "anomaly": cmd_anomaly,
        "demo": cmd_demo,
        "macro": cmd_macro,
        "session": cmd_session,
        "run": cmd_run,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
