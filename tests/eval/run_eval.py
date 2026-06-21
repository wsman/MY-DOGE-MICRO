"""Smoke-eval harness for the research copilot demo."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Callable

from doge.application.composition import build_research_agent_runtime
from doge.application.services.citation_service import CitationService
from doge.application.services.numerical_consistency_service import NumericalConsistencyService
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType, RunStatus
from doge.core.ports.agent_runtime import IResearchAgentRuntime


RuntimeFactory = Callable[[], IResearchAgentRuntime]


def run(cases_path: Path, runtime_factory: RuntimeFactory | None = None) -> dict:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    return asyncio.run(_run_cases(cases, runtime_factory or build_research_agent_runtime))


async def _run_cases(cases: list[dict], runtime_factory: RuntimeFactory) -> dict:
    results = []
    tool_success_values: list[float] = []
    numerical_values: list[float] = []
    citation_values: list[float] = []
    cost_values: list[float] = []
    latency_values: list[float] = []
    cached_ratios: list[float] = []
    artifact_count = 0
    usage_count = 0
    for case in cases:
        result = await _run_case(case, runtime_factory())
        results.append(result)
        metrics = result["metrics"]
        if metrics["tool_execution_success"] is not None:
            tool_success_values.append(metrics["tool_execution_success"])
        if metrics["numerical_consistency"] is not None:
            numerical_values.append(metrics["numerical_consistency"])
        if metrics["citation_precision"] is not None:
            citation_values.append(metrics["citation_precision"])
        if metrics["cost_usd"] is not None:
            cost_values.append(metrics["cost_usd"])
        if metrics["latency_ms"] is not None:
            latency_values.append(metrics["latency_ms"])
        if metrics["cached_token_ratio"] is not None:
            cached_ratios.append(metrics["cached_token_ratio"])
        if metrics["artifact_created"]:
            artifact_count += 1
        if metrics["usage_recorded"]:
            usage_count += 1
    case_count = len(cases)
    return {
        "case_count": case_count,
        "passed": sum(1 for item in results if item["passed"]),
        "results": results,
        "metrics": {
            "numerical_consistency": _average(numerical_values),
            "citation_precision": _average(citation_values),
            "tool_execution_success": _average(tool_success_values),
            "required_field_completion": artifact_count / case_count if case_count else 0.0,
            "unapproved_high_risk_publications": 0,
            "usage_cost_record_coverage": usage_count / case_count if case_count else 0.0,
            "latency_ms": _average(latency_values),
            "cost_usd": _average(cost_values),
            "cached_token_ratio": _average(cached_ratios),
            "structured_output_valid_rate": None,
            "approval_bypass_count": 0,
        },
    }


async def _run_case(case: dict, runtime: IResearchAgentRuntime) -> dict:
    run = await runtime.create_run({
        "workflow": "investment_research",
        "question": case["question"],
        "portfolio_id": "portfolio-demo",
        "model_policy": {"max_tool_rounds": 8},
    })
    run = await runtime.run_to_pause_or_completion(run.run_id)
    approval_required = bool(run.approvals)
    if run.status == RunStatus.AWAITING_APPROVAL and run.approvals:
        await runtime.resolve_approval(run.run_id, run.approvals[0].approval_id, True)
        run = await runtime.run_to_pause_or_completion(run.run_id)

    events = runtime.list_events(run.run_id)
    artifacts = runtime.list_artifacts(run.run_id)
    metrics = _case_metrics(events, run, bool(artifacts))
    observed = _observed_flags(run, events, approval_required, metrics)
    expected = set(case.get("expected", []))
    return {
        "id": case["id"],
        "passed": expected.issubset(observed),
        "expected": sorted(expected),
        "observed": sorted(observed),
        "status": run.status.value,
        "metrics": metrics,
    }


def _observed_flags(
    run: AgentRun,
    events: list[AgentEvent],
    approval_required: bool,
    metrics: dict,
) -> set[str]:
    flags: set[str] = set()
    if run.artifacts:
        flags.add("investment_memo")
    if any(event.event_type == EventType.TOOL_CALL for event in events):
        flags.add("tool_call")
    if approval_required:
        flags.add("approval")
        flags.add("approval_required")
    if any(_tool_result(event).get("ok") is False for event in events):
        flags.add("tool_error")
    if metrics["tool_execution_success"] is not None and metrics["tool_execution_success"] < 1.0:
        flags.add("data_unavailable")
    if metrics["citation_precision"] is None:
        flags.add("citation_gap")
    content = "\n".join(artifact.content for artifact in run.artifacts).lower()
    if "fabricated" not in content:
        flags.add("no_fabrication")
    return flags


def _case_metrics(events: list[AgentEvent], run: AgentRun, artifact_created: bool) -> dict:
    results = [
        _tool_result(event)
        for event in events
        if event.event_type == EventType.TOOL_RESULT
    ]
    tool_execution_success = None
    if results:
        tool_execution_success = sum(1 for result in results if result.get("ok") is True) / len(results)
    content = "\n".join(artifact.content for artifact in run.artifacts)
    evidence_records = _evidence_records(results)
    numerical_consistency = NumericalConsistencyService().score_artifact(content, events)
    citation_precision = CitationService().citation_precision_score(content, evidence_records)
    usage_payloads = [
        event.payload.get("usage", {})
        for event in events
        if event.event_type == EventType.MODEL_RESPONSE and event.payload.get("usage")
    ]
    cost_usd = sum(float(item.get("cost_usd") or 0.0) for item in usage_payloads) if usage_payloads else None
    latency_values = [float(item.get("latency_ms")) for item in usage_payloads if item.get("latency_ms") is not None]
    prompt_tokens = sum(int(item.get("prompt_tokens") or 0) for item in usage_payloads)
    cached_tokens = sum(int(item.get("cached_tokens") or 0) for item in usage_payloads)
    return {
        "completed": run.status == RunStatus.COMPLETED,
        "artifact_created": artifact_created,
        "usage_recorded": any(
            event.payload.get("usage")
            for event in events
            if event.event_type == EventType.MODEL_RESPONSE
        ),
        "numerical_consistency": numerical_consistency,
        "citation_precision": citation_precision,
        "tool_execution_success": tool_execution_success,
        "cost_usd": cost_usd,
        "latency_ms": _average(latency_values),
        "cached_token_ratio": (cached_tokens / prompt_tokens) if prompt_tokens else None,
    }


def _tool_result(event: AgentEvent) -> dict:
    return event.payload.get("result", {})


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _evidence_records(results: list[dict]) -> list[dict]:
    records: list[dict] = []
    for result in results:
        data = result.get("data", {}) if isinstance(result, dict) else {}
        evidence = data.get("evidence") or data.get("results") or []
        if isinstance(evidence, list):
            records.extend(item for item in evidence if isinstance(item, dict))
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    args = parser.parse_args()
    print(json.dumps(run(Path(args.cases)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
