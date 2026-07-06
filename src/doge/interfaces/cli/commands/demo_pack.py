"""CLI command: demo-pack."""

from __future__ import annotations

import sys
from pathlib import Path

from doge.bootstrap import build_runtime_container
from doge.platform.evidence import DemoPackExporter
from doge.shared.scope import TenantScope


def cmd_demo_pack(args) -> None:
    run_id = getattr(args, "run_id", None) or getattr(args, "case", None)
    if not run_id:
        print("demo-pack failed: --run-id or --case is required", file=sys.stderr)
        sys.exit(2)
        return
    try:
        container = _runtime_container()
        runtime = container.build_persisted_research_agent_runtime()
        exporter = DemoPackExporter(
            runtime,
            container.build_run_summary_use_case(runtime=runtime),
        )
        result = exporter.export(run_id, Path(args.output), scope=TenantScope.local())
    except Exception as exc:  # noqa: BLE001 - CLI emits concise operator message
        print(f"demo-pack failed: {exc}", file=sys.stderr)
        sys.exit(1)
        return

    print(f"demo_pack={result.output_dir}")
    for name in sorted(result.files):
        print(f"{name}={result.files[name]}")


def _runtime_container():
    return build_runtime_container()
