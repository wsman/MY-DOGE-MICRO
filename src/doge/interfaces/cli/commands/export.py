"""CLI command: export."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from doge.bootstrap import build_runtime_container
from doge.core.security import redact_secrets
from doge.shared.scope import TenantScope


def cmd_export(args) -> None:
    """Export a persisted research-agent run as Markdown or JSON."""
    run_id = getattr(args, "run_id", None)
    if not run_id:
        print("export failed: run_id is required", file=sys.stderr)
        sys.exit(2)
        return

    try:
        container = _runtime_container()
        runtime = container.build_persisted_research_agent_runtime()
        scope = TenantScope.local()
        run = runtime.get_run(scope, run_id)
        if run is None:
            print(f"export failed: run not found: {run_id}", file=sys.stderr)
            sys.exit(1)
            return
        summary = container.build_run_summary_use_case(runtime=runtime).build(run, scope=scope)
        content = _render(summary, fmt=args.format, citations_only=args.citations_only)
        output = getattr(args, "output", None)
        if output:
            Path(output).write_text(content, encoding="utf-8")
        else:
            print(content, end="" if content.endswith("\n") else "\n")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - CLI emits concise operator message
        print(f"export failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _render(summary: dict[str, Any], *, fmt: str, citations_only: bool) -> str:
    if fmt == "json":
        payload = {
            "summary": summary.get("summary", {}),
            "claims": summary.get("claims", []),
            "citations": summary.get("citations", []),
            "eval": summary.get("eval", {}),
        }
        if citations_only:
            payload = {"citations": payload["citations"]}
        return json.dumps(redact_secrets(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    redacted_summary = redact_secrets(summary)
    rendered = _render_markdown(redacted_summary, citations_only=citations_only)
    return str(redact_secrets(rendered))


def _render_markdown(summary: dict[str, Any], *, citations_only: bool) -> str:
    if citations_only:
        return _citations_markdown(summary.get("citations", []))

    run_summary = summary.get("summary", {})
    title = "Investment Memo"
    body = str(run_summary.get("summary_text") or "").strip()
    lines = [f"# {title}", ""]
    if body:
        lines.append(body)
        lines.append("")
    else:
        lines.extend(["No investment memo artifact is available for this run.", ""])

    lines.append("## Claims")
    claims = summary.get("claims", [])
    if not claims:
        lines.append("- No structured claims available.")
    for claim in claims:
        status = claim.get("support_status") or claim.get("status") or "unknown"
        text = claim.get("claim_text") or claim.get("text") or ""
        lines.append(f"- [{status}] {text}")
    lines.append("")
    lines.append(_citations_markdown(summary.get("citations", [])).rstrip())
    return "\n".join(lines).rstrip() + "\n"


def _citations_markdown(citations: list[dict[str, Any]]) -> str:
    lines = ["## Citations"]
    if not citations:
        lines.append("- No citations available.")
        return "\n".join(lines) + "\n"
    for citation in citations:
        label = _citation_label(citation)
        snippet = str(citation.get("snippet") or "").strip()
        suffix = f" — {snippet}" if snippet else ""
        lines.append(f"- {label}{suffix}")
    return "\n".join(lines) + "\n"


def _citation_label(citation: dict[str, Any]) -> str:
    parts = [
        str(citation.get("source") or citation.get("document_id") or citation.get("citation_id") or "citation"),
    ]
    page = citation.get("page_number") or citation.get("page_id")
    if page is not None:
        parts.append(f"p.{page}")
    chunk = citation.get("chunk_id") or citation.get("evidence_id")
    if chunk:
        parts.append(str(chunk))
    return " ".join(parts)


def _runtime_container():
    return build_runtime_container()
