"""Build local demo packets from persisted run state."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun
from doge.core.security import redact_secrets
from doge.shared.scope import TenantScope


@dataclass(frozen=True)
class DemoPackResult:
    run_id: str
    output_dir: Path
    files: dict[str, Path]


class DemoPackExporter:
    """Export reviewer-facing artifacts for one persisted run."""

    def __init__(self, runtime: Any, run_summary_use_case: Any) -> None:
        self._runtime = runtime
        self._run_summary = run_summary_use_case

    def export(
        self,
        run_id: str,
        output_dir: Path | str,
        *,
        scope: TenantScope | None = None,
    ) -> DemoPackResult:
        resolved_scope = scope or TenantScope.local()
        run = self._runtime.get_run(resolved_scope, run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        events = self._runtime.list_events(resolved_scope, run_id)
        artifacts = self._runtime.list_artifacts(resolved_scope, run_id)
        summary = self._run_summary.build(run, scope=resolved_scope)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        latest_artifact = _latest_investment_memo(artifacts)
        files = {
            "run_summary.md": output_path / "run_summary.md",
            "investment_memo.md": output_path / "investment_memo.md",
            "trace.jsonl": output_path / "trace.jsonl",
            "citations.json": output_path / "citations.json",
            "metrics.json": output_path / "metrics.json",
            "speaker_notes.md": output_path / "speaker_notes.md",
        }
        files["run_summary.md"].write_text(_run_summary_markdown(run, summary, events, artifacts), encoding="utf-8")
        files["investment_memo.md"].write_text(_artifact_markdown(latest_artifact), encoding="utf-8")
        files["trace.jsonl"].write_text(_trace_jsonl(events), encoding="utf-8")
        files["citations.json"].write_text(_json({"citations": summary["citations"]}), encoding="utf-8")
        files["metrics.json"].write_text(_json(_metrics_payload(run, summary, events, artifacts)), encoding="utf-8")
        files["speaker_notes.md"].write_text(_speaker_notes_markdown(run, summary, latest_artifact), encoding="utf-8")
        return DemoPackResult(run_id=run.run_id, output_dir=output_path, files=files)


def _run_summary_markdown(
    run: AgentRun,
    summary: dict[str, Any],
    events: list[AgentEvent],
    artifacts: list[AgentArtifact],
) -> str:
    claims = summary["claims"]
    citations = summary["citations"]
    evaluation = summary["eval"]
    lines = [
        f"# Run Summary - {run.run_id}",
        "",
        f"- Status: {_status_value(run)}",
        f"- Workflow: {run.workflow}",
        f"- Question: {run.question}",
        f"- Events: {len(events)}",
        f"- Artifacts: {len(artifacts)}",
        f"- Claims: {len(claims)}",
        f"- Citations: {len(citations)}",
        f"- Coverage ratio: {evaluation.get('coverage_ratio', 'n/a')}",
        "",
        "## Claims",
    ]
    if not claims:
        lines.append("- No structured claims available.")
    for claim in claims:
        lines.append(f"- [{claim.get('support_status')}] {claim.get('claim_text')}")
    return "\n".join(lines) + "\n"


def _artifact_markdown(artifact: AgentArtifact | None) -> str:
    if artifact is None:
        return "# Investment Memo\n\nNo investment memo artifact is available for this run.\n"
    title = artifact.title or "Investment Memo"
    return f"# {title}\n\n{artifact.content.rstrip()}\n"


def _latest_investment_memo(artifacts: list[AgentArtifact]) -> AgentArtifact | None:
    return next((artifact for artifact in reversed(artifacts) if artifact.kind == "investment_memo"), None)


def _trace_jsonl(events: list[AgentEvent]) -> str:
    records = [
        json.dumps(redact_secrets(_serialize(event)), ensure_ascii=False, sort_keys=True)
        for event in events
    ]
    return "\n".join(records) + ("\n" if records else "")


def _metrics_payload(
    run: AgentRun,
    summary: dict[str, Any],
    events: list[AgentEvent],
    artifacts: list[AgentArtifact],
) -> dict[str, Any]:
    evaluation = summary["eval"]
    return {
        "run_id": run.run_id,
        "status": _status_value(run),
        "event_count": len(events),
        "artifact_count": len(artifacts),
        "claim_count": len(summary["claims"]),
        "citation_count": len(summary["citations"]),
        "eval": evaluation,
        "metrics": evaluation.get("metrics", {}),
    }


def _speaker_notes_markdown(
    run: AgentRun,
    summary: dict[str, Any],
    artifact: AgentArtifact | None,
) -> str:
    lines = [
        f"# Speaker Notes - {run.run_id}",
        "",
        "## Walkthrough",
        "1. Open `run_summary.md` for the run question, status, claims, and citation count.",
        "2. Open `investment_memo.md` for the generated memo artifact.",
        "3. Open `trace.jsonl` to inspect event ordering and tool/model payloads.",
        "4. Open `citations.json` and `metrics.json` for evidence and evaluation details.",
        "",
        "## Talking Points",
        f"- Workflow: {run.workflow}",
        f"- Run status: {_status_value(run)}",
        f"- Claims: {len(summary['claims'])}",
        f"- Citations: {len(summary['citations'])}",
        f"- Memo artifact: {'available' if artifact else 'not available'}",
        "",
        "## Boundaries",
        "- This packet is local evidence for a single run.",
        "- It does not close external analyst, provider, auth, or registry gates.",
    ]
    return "\n".join(lines) + "\n"


def _json(payload: Any) -> str:
    return json.dumps(redact_secrets(_serialize(payload)), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _serialize(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {key: _serialize(value) for key, value in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    return obj


def _status_value(run: AgentRun) -> str:
    return str(getattr(run.status, "value", run.status))
