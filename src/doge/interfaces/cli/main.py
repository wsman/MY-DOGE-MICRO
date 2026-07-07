"""Canonical CLI entrypoint for MY-DOGE-MICRO.

Usage:
    doge stock <ticker> [--market cn] [--days 20]
    doge rsrs [--market cn] [--top 20]
    doge breadth [--market cn] [--days 10]
    doge brief [--market cn] [--top 20]
    doge anomaly [--min-ratio 3.0] [--top 20]
    doge demo [--market cn] [--top 5]
    doge demo-pack --run-id <run_id> --output demo_packet/
    doge export <run_id> [--format md|json] [--citations-only] [--output memo.md]
    doge macro [--verbose]
    doge doctor [--json]
    doge session [--title "..."]
    doge run "question" [--session <session_id>] [--json] [--trace] [--follow] [--jsonl]
    doge run --resume <run_id> [--approval <approval_id>] [--deny]
    doge batch --cases cases.json [--output results.json]
    doge start [--path {cli,daemon,web,demo,doctor}]
    doge template list|show|seed
    doge case list|show|preflight|execute|review|decision

Clean-architecture wiring (ADR-0001 / ADR-0010): each subcommand delegates to
its read-only service or application use case via ``doge.bootstrap`` containers.
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
    cmd_batch,
    cmd_brief,
    cmd_breadth,
    cmd_case,
    cmd_demo,
    cmd_demo_pack,
    cmd_doctor,
    cmd_export,
    cmd_macro,
    cmd_run,
    cmd_rsrs,
    cmd_session,
    cmd_slots,
    cmd_start,
    cmd_stock,
    cmd_template,
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

    # brief
    p_brief = sub.add_parser("brief", help="console market brief (CN local data)")
    p_brief.add_argument("--market", default="cn", choices=["cn", "us"])
    p_brief.add_argument("--top", type=int, default=20)

    # anomaly
    p_anomaly = sub.add_parser("anomaly", help="volume anomaly detection")
    p_anomaly.add_argument("--min-ratio", type=float, default=3.0)
    p_anomaly.add_argument("--top", type=int, default=20)

    # demo
    p_demo = sub.add_parser("demo", help="5-minute demo using bundled sample data")
    p_demo.add_argument("--market", default="cn", choices=["cn", "us"])
    p_demo.add_argument("--top", type=int, default=5)

    # demo-pack
    p_demo_pack = sub.add_parser("demo-pack", help="export a local demo packet for a persisted run")
    p_demo_pack.add_argument("--run-id", help="persisted run id to export")
    p_demo_pack.add_argument("--case", help="alias for --run-id; retained for roadmap wording")
    p_demo_pack.add_argument("--output", required=True, help="output directory for packet files")

    # export
    p_export = sub.add_parser("export", help="export a persisted research-agent memo")
    p_export.add_argument("run_id", help="persisted run id to export")
    p_export.add_argument("--format", default="md", choices=["md", "json"], help="export format")
    p_export.add_argument("--citations-only", action="store_true", help="export citations without memo body")
    p_export.add_argument("--output", help="write output to path instead of stdout")

    # macro
    p_macro = sub.add_parser("macro", help="macro strategy report via configured text LLM")
    p_macro.add_argument("--market", default="cn", choices=["cn", "us"])
    p_macro.add_argument("--verbose", action="store_true", help="verbose output")
    p_macro.add_argument("--config-file", help="ignored — accepted for forward compatibility")

    # doctor
    p_doctor = sub.add_parser("doctor", help="run local diagnostics")
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.add_argument(
        "--next",
        action="store_true",
        help="print environment-aware next-step guidance per failing check",
    )

    # start
    p_start = sub.add_parser(
        "start", help="first-run launcher: choose a path"
    )
    p_start.add_argument(
        "--path",
        choices=["cli", "daemon", "web", "demo", "doctor"],
        help="non-interactive path dispatch",
    )

    # session
    p_session = sub.add_parser("session", help="create or resume an agent session")
    p_session.add_argument("--title", default="Research session")
    p_session.add_argument("--resume", help="session id to resume")
    p_session.add_argument("--message", help="execute one message in the resumed session")
    p_session.add_argument("--market", default="us", choices=["cn", "us"])
    p_session.add_argument("--mode", default="embedded", choices=["embedded", "gateway"])
    p_session.add_argument("--approve", help="approval id or run_id:approval_id to approve")
    p_session.add_argument("--deny", help="approval id or run_id:approval_id to deny")
    p_session.add_argument("--cancel", help="run id to cancel")
    p_session.add_argument("--daemon-url", default="http://127.0.0.1:8901")
    p_session.add_argument("--api-token", help="bearer token for gateway mode")
    p_session.add_argument("--list", action="store_true", help="list recent sessions")
    p_session.add_argument("--limit", type=int, default=20)
    p_session.add_argument("--interactive", action="store_true", help="enter an interactive session loop")
    p_session.add_argument("--follow", action="store_true", help="follow gateway run events after creating a turn")
    p_session.add_argument("--jsonl", action="store_true", help="emit gateway run events as JSON Lines")

    # run
    p_run = sub.add_parser("run", help="execute a persisted research-agent run")
    p_run.add_argument("question", nargs="?", help="research question")
    p_run.add_argument("--resume", help="run id to resume")
    p_run.add_argument("--approval", help="approval id to resolve before resuming")
    p_run.add_argument("--deny", action="store_true", help="deny the approval instead of approving it")
    p_run.add_argument("--session", help="attach the run to an existing session")
    p_run.add_argument("--market", default="us", choices=["cn", "us"])
    p_run.add_argument("--language", default="en")
    p_run.add_argument("--portfolio", default=None)
    p_run.add_argument("--max-tool-rounds", type=int, default=8)
    p_run.add_argument("--json", action="store_true", help="emit JSON only")
    p_run.add_argument("--trace", action="store_true", help="print event trace after the summary")
    p_run.add_argument("--follow", action="store_true", help="print run events after the summary")
    p_run.add_argument("--jsonl", action="store_true", help="emit run summary and events as JSON Lines")

    # batch
    p_batch = sub.add_parser("batch", help="run offline deterministic research-agent cases")
    p_batch.add_argument("--cases", required=True, help="case file path")
    p_batch.add_argument("--output", help="write result to path instead of stdout")
    p_batch.add_argument("--format", default="json", choices=["json", "markdown"])
    p_batch.add_argument("--auto-approve", action=argparse.BooleanOptionalAction, default=True)
    p_batch.add_argument("--max-tool-rounds", type=int, default=8)

    # template
    p_template = sub.add_parser("template", help="manage workflow templates")
    template_sub = p_template.add_subparsers(dest="template_cmd", required=True)
    p_template_list = template_sub.add_parser("list", help="list workflow templates")
    p_template_list.add_argument("--limit", type=int, default=100)
    p_template_list.add_argument("--json", action="store_true")
    p_template_show = template_sub.add_parser("show", help="show a workflow template")
    p_template_show.add_argument("template_id", help="template id or slug")
    p_template_show.add_argument("--json", action="store_true")
    p_template_seed = template_sub.add_parser("seed", help="seed built-in workflow templates")
    p_template_seed.add_argument("--dry-run", action="store_true")
    p_template_seed.add_argument("--json", action="store_true")

    # slots (ADR-0042; experimental, feature-flagged)
    p_slots = sub.add_parser("slots", help="list and inspect platform slots (experimental)")
    slots_sub = p_slots.add_subparsers(dest="slots_cmd", required=True)
    p_slots_list = slots_sub.add_parser("list", help="list registered slots")
    p_slots_list.add_argument("--json", action="store_true")
    p_slots_show = slots_sub.add_parser("show", help="show a slot manifest + health + declared tools")
    p_slots_show.add_argument("slot_id", help="slot id (e.g. market.core)")
    p_slots_show.add_argument("--json", action="store_true")
    p_slots_bundle = slots_sub.add_parser("bundle", help="list or activate slot bundles")
    slots_bundle_sub = p_slots_bundle.add_subparsers(dest="bundle_cmd", required=True)
    p_slots_bundle_list = slots_bundle_sub.add_parser("list", help="list slot bundles")
    p_slots_bundle_list.add_argument("--json", action="store_true")
    p_slots_bundle_activate = slots_bundle_sub.add_parser("activate", help="activate a slot bundle")
    p_slots_bundle_activate.add_argument("bundle_id", help="bundle id (e.g. bundle.local_analyst)")
    p_slots_bundle_activate.add_argument("--json", action="store_true")
    p_slots_install = slots_sub.add_parser("install", help="install a local slot manifest preview")
    p_slots_install.add_argument("source", help="slot manifest JSON file or directory containing slot.json")
    p_slots_install.add_argument("--json", action="store_true")

    # case
    p_case = sub.add_parser("case", help="operate a research case workspace")
    case_sub = p_case.add_subparsers(dest="case_cmd", required=True)
    p_case_list = case_sub.add_parser("list", help="list research cases")
    p_case_list.add_argument("--project-id")
    p_case_list.add_argument("--limit", type=int, default=100)
    p_case_list.add_argument("--json", action="store_true")
    p_case_show = case_sub.add_parser("show", help="show case review state")
    p_case_show.add_argument("case_id")
    p_case_show.add_argument("--json", action="store_true")
    for name, help_text in (
        ("preflight", "preflight a template execution"),
        ("execute", "execute a workflow template"),
    ):
        p_case_exec = case_sub.add_parser(name, help=help_text)
        p_case_exec.add_argument("case_id")
        p_case_exec.add_argument("template_id")
        p_case_exec.add_argument("--question")
        p_case_exec.add_argument("--workflow")
        p_case_exec.add_argument("--session-id")
        p_case_exec.add_argument("--market", default="us", choices=["cn", "us"])
        p_case_exec.add_argument("--language", default="en")
        p_case_exec.add_argument("--document-id", action="append")
        p_case_exec.add_argument("--portfolio-id")
        p_case_exec.add_argument("--model-policy")
        p_case_exec.add_argument("--inputs")
        p_case_exec.add_argument("--json", action="store_true")
        if name == "execute":
            p_case_exec.add_argument("--skip-preflight", action="store_true")
    p_case_review = case_sub.add_parser("review", help="show case review state")
    p_case_review.add_argument("case_id")
    p_case_review.add_argument("--json", action="store_true")
    p_case_decision = case_sub.add_parser("decision", help="record a case decision")
    p_case_decision.add_argument("case_id")
    p_case_decision.add_argument("--decision", required=True, choices=["approve", "reject", "hold", "escalate"])
    p_case_decision.add_argument("--rationale")
    p_case_decision.add_argument("--source-run-id", action="append")
    p_case_decision.add_argument("--source-execution-id", action="append")
    p_case_decision.add_argument("--json", action="store_true")

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
        "batch": cmd_batch,
        "brief": cmd_brief,
        "demo": cmd_demo,
        "doctor": cmd_doctor,
        "export": cmd_export,
        "macro": cmd_macro,
        "session": cmd_session,
        "slots": cmd_slots,
        "start": cmd_start,
        "run": cmd_run,
        "template": cmd_template,
        "case": cmd_case,
        "demo-pack": cmd_demo_pack,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
