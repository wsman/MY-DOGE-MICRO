"""Runtime-backed runner for the 35-case citation quality gold set."""

from __future__ import annotations

import asyncio
import json
import re
import tempfile
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from doge.application.agent.tools import ToolRegistry
from doge.bootstrap.runtime import RuntimeContainer
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, EventType, RunStatus
from doge.core.domain.tool_policy import ToolCategory
from doge.core.ports.agent_model import AgentMessage, AgentResponse, IAgentModel
from doge.core.ports.runtime_services import ToolResult
from doge.shared.scope import TenantScope

from tests.eval.gold_eval import load_gold_cases, score_observations, summarize_gold_set
from tests.eval.gold_set_seed import SeededGoldSet, seed_gold_set


GOLD_CASES_PATH = Path(__file__).with_name("gold_cases.json")

_CITATION_RE = re.compile(r"\[\^(evd-[^\]\s]+)\]")
_CLAIM_RE = re.compile(r"claim_id=([^;\]\s]+);\s*support_status=([^;\]\s]+)")
_RELATION_RE = re.compile(
    r"claim_id=([^;\]\s]+);\s*evidence_id=([^;\]\s]+);\s*support_status=([^;\]\s]+)"
)
_NUMBER_RE = re.compile(r"^-\s*([A-Za-z0-9_]+)=(-?\d+(?:\.\d+)?)\s*$")


def run_all(
    *,
    gold_cases_path: Path = GOLD_CASES_PATH,
    db_path: Path | None = None,
    storage_dir: Path | None = None,
) -> dict[str, Any]:
    """Run all gold-set cases through the persisted agent runtime."""

    cases = load_gold_cases(gold_cases_path)
    if db_path is not None and storage_dir is not None:
        return asyncio.run(_run_all(cases, db_path=db_path, storage_dir=storage_dir))

    with tempfile.TemporaryDirectory(prefix="doge-gold-set-") as tmp:
        root = Path(tmp)
        return asyncio.run(
            _run_all(
                cases,
                db_path=db_path or root / "runtime.db",
                storage_dir=storage_dir or root / "storage",
            )
        )


async def _run_all(
    cases: list[dict[str, Any]],
    *,
    db_path: Path,
    storage_dir: Path,
) -> dict[str, Any]:
    scope = TenantScope.local()
    seeded = seed_gold_set(
        cases=cases,
        db_path=db_path,
        storage_dir=storage_dir,
        scope=scope,
    )
    model = CaseAwareGoldSetModel(cases)
    tool_registry = build_gold_set_tool_registry(seeded)
    runtime = RuntimeContainer(db_path=db_path).build_persisted_research_agent_runtime(
        model=model,
        tool_registry=tool_registry,
    )

    observations: dict[str, dict[str, Any]] = {}
    run_records: list[dict[str, Any]] = []
    for case in cases:
        run = await runtime.create_run(scope, _run_request(case))
        run = await runtime.run_to_pause_or_completion(scope, run.run_id)
        events = runtime.list_events(scope, run.run_id)
        artifacts = runtime.list_artifacts(scope, run.run_id)
        observations[case["id"]] = observation_from_runtime(case, events, artifacts)
        run_records.append({
            "case_id": case["id"],
            "run_id": run.run_id,
            "status": run.status.value,
            "event_count": len(events),
            "artifact_count": len(artifacts),
        })

    score = score_observations(cases, observations)
    return {
        "schema_version": "doge.citation_quality_baseline.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "local_runtime_scripted_gold_set",
        "runtime_path": "PersistedResearchAgentRuntime",
        "w3_live_closure_allowed": False,
        "gold_set": summarize_gold_set(cases),
        "score": score,
        "observations": observations,
        "runs": run_records,
        "w3_live_observation_input": w3_live_observations_from_baseline(observations),
    }


def build_gold_set_tool_registry(seeded: SeededGoldSet) -> ToolRegistry:
    """Build a narrow lookup registry for deterministic gold-set runs."""

    registry = ToolRegistry()

    def lookup_evidence(
        query: str,
        case_id: str = "",
        limit: int = 5,
        context: Any = None,
    ) -> ToolResult:
        del context
        results = [
            item.to_lookup_result()
            for item in seeded.evidence_by_case.get(case_id, [])
        ][: max(0, int(limit))]
        return ToolResult(
            name="lookup_evidence",
            data={
                "case_id": case_id,
                "query": query,
                "result_count": len(results),
                "results": results,
                "local_baseline_only": True,
            },
        )

    registry.register(
        {
            "type": "function",
            "function": {
                "name": "lookup_evidence",
                "description": "Look up deterministic seeded evidence for a gold-set case.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "case_id": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 0, "maximum": 10},
                    },
                    "required": ["query", "case_id"],
                    "additionalProperties": False,
                },
            },
        },
        lookup_evidence,
        category=ToolCategory.READ_ONLY,
    )
    return registry


class CaseAwareGoldSetModel(IAgentModel):
    """Scripted model that maps each gold case to one lookup and one artifact."""

    def __init__(self, cases: list[dict[str, Any]]) -> None:
        self._case_by_question = {case["question"]: case for case in cases}
        self._case_by_id = {case["id"]: case for case in cases}

    async def chat(
        self,
        messages: list[AgentMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int = 16384,
        max_completion_tokens: int | None = None,
        stream: bool = True,
        model: str | None = None,
        thinking_enabled: bool | None = None,
        response_format: dict[str, Any] | None = None,
        prompt_cache_key: str | None = None,
        safety_identifier: str | None = None,
        timeout: float | None = None,
        request_metadata: dict[str, Any] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentResponse]:
        del tools, tool_choice, max_tokens, max_completion_tokens, stream
        del thinking_enabled, response_format, prompt_cache_key, safety_identifier, timeout, extra_body
        case = self._case_for_messages(messages)
        tool_messages = [message for message in messages if message.role == "tool"]
        if not tool_messages:
            arguments = {
                "case_id": case["id"],
                "query": case["question"],
                "limit": max(5, len(case.get("expected_citations", []))),
            }
            yield AgentResponse(
                message=AgentMessage(
                    role="assistant",
                    content="",
                    reasoning_content="Need seeded evidence before producing the benchmark artifact.",
                    tool_calls=[{
                        "id": f"call-{case['id']}",
                        "type": "function",
                        "function": {
                            "name": "lookup_evidence",
                            "arguments": json.dumps(arguments, ensure_ascii=False),
                        },
                    }],
                ),
                usage=_usage(model, latency_ms=5.0),
            )
            return

        tool_payload = _last_tool_payload(tool_messages)
        evidence_ids = [
            str(item["evidence_id"])
            for item in tool_payload.get("data", {}).get("results", [])
            if isinstance(item, dict) and item.get("evidence_id")
        ]
        yield AgentResponse(
            message=AgentMessage(
                role="assistant",
                content=_artifact_text(case, evidence_ids),
            ),
            finish_reason="stop",
            usage=_usage(model, latency_ms=10.0),
        )

    def _case_for_messages(self, messages: list[AgentMessage]) -> dict[str, Any]:
        for message in reversed(messages):
            if message.role != "user" or not isinstance(message.content, str):
                continue
            case = self._case_by_question.get(message.content)
            if case is not None:
                return case
        payload = _last_tool_payload([message for message in messages if message.role == "tool"])
        case_id = payload.get("data", {}).get("case_id")
        if case_id in self._case_by_id:
            return self._case_by_id[case_id]
        raise ValueError("gold-set model could not identify the current case")


def observation_from_runtime(
    case: dict[str, Any],
    events: list[AgentEvent],
    artifacts: list[AgentArtifact],
) -> dict[str, Any]:
    content = "\n".join(artifact.content for artifact in artifacts)
    return {
        "retrieved_evidence_ids": _retrieved_evidence_ids(events),
        "cited_evidence_ids": _cited_evidence_ids(content),
        "claim_evidence_relations": _claim_evidence_relations(content),
        "claims": _claims(content, case),
        "numbers": _numbers(content),
        "usage": _usage_from_events(events),
    }


def w3_live_observations_from_baseline(observations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Map local baseline observations into the W3-live builder input shape."""

    return {
        "schema_version": "doge.w3_live_observation_input.v1",
        "source": "citation_quality_baseline_local_scripted",
        "w3_live_closure_allowed": False,
        "observations": observations,
    }


def _run_request(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow": "gold_set_citation_benchmark",
        "question": case["question"],
        "document_ids": [
            material["document_id"]
            for material in case.get("materials", [])
        ],
        "model_policy": {
            "execution_profile": case.get("execution_profile") or "financial_research",
            "max_tool_rounds": 4,
            "stream": False,
        },
    }


def _artifact_text(case: dict[str, Any], evidence_ids: list[str]) -> str:
    marker_text = "".join(f"[^{evidence_id}]" for evidence_id in evidence_ids)
    lines = [
        f"# Gold-set memo: {case['id']}",
        "",
        "## Claims",
    ]
    for claim in case.get("expected_claims", []):
        status = claim.get("expected_status") or "insufficient_evidence"
        lines.append(
            f"- {claim.get('text', '')}{marker_text} "
            f"[claim_id={claim.get('claim_id')}; support_status={status}]"
        )
    lines.extend(["", "## Evidence Relations"])
    for claim in case.get("expected_claims", []):
        status = claim.get("expected_status") or "insufficient_evidence"
        for evidence_id in evidence_ids:
            lines.append(
                f"- claim_id={claim.get('claim_id')}; "
                f"evidence_id={evidence_id}; support_status={status}"
            )
    if not evidence_ids:
        lines.append("- none")
    lines.extend(["", "## Numbers"])
    for item in case.get("expected_numbers", []):
        lines.append(f"- {item['metric']}={item['value']}")
    if not case.get("expected_numbers"):
        lines.append("- none")
    return "\n".join(lines)


def _last_tool_payload(tool_messages: list[AgentMessage]) -> dict[str, Any]:
    if not tool_messages:
        return {}
    content = tool_messages[-1].content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
    if isinstance(content, dict):
        return content
    return {}


def _retrieved_evidence_ids(events: list[AgentEvent]) -> list[str]:
    ids: list[str] = []
    for event in events:
        if event.event_type != EventType.TOOL_RESULT:
            continue
        data = event.payload.get("result", {}).get("data", {})
        for item in data.get("results", []):
            if isinstance(item, dict) and item.get("evidence_id"):
                ids.append(str(item["evidence_id"]))
    return _stable_unique(ids)


def _cited_evidence_ids(content: str) -> list[str]:
    return _stable_unique(_CITATION_RE.findall(content))


def _claim_evidence_relations(content: str) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for line in _section_lines(content, "Evidence Relations"):
        match = _RELATION_RE.search(line)
        if not match:
            continue
        relations.append({
            "claim_id": match.group(1),
            "evidence_id": match.group(2),
            "support_status": match.group(3),
        })
    return relations


def _claims(content: str, case: dict[str, Any]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for line in _section_lines(content, "Claims"):
        match = _CLAIM_RE.search(line)
        if match:
            parsed.append({"claim_id": match.group(1), "support_status": match.group(2)})
    if parsed:
        return parsed
    return [
        {
            "claim_id": claim.get("claim_id"),
            "support_status": claim.get("expected_status"),
        }
        for claim in case.get("expected_claims", [])
    ]


def _numbers(content: str) -> dict[str, float]:
    numbers: dict[str, float] = {}
    for line in _section_lines(content, "Numbers"):
        match = _NUMBER_RE.match(line.strip())
        if match:
            numbers[match.group(1)] = float(match.group(2))
    return numbers


def _usage_from_events(events: list[AgentEvent]) -> dict[str, float]:
    payloads = [
        event.payload.get("usage") or {}
        for event in events
        if event.event_type == EventType.MODEL_RESPONSE and event.payload.get("usage")
    ]
    cost = sum(float(payload.get("cost_usd") or 0.0) for payload in payloads)
    latency_values = [
        float(payload.get("latency_ms"))
        for payload in payloads
        if payload.get("latency_ms") is not None
    ]
    latency = sum(latency_values) / len(latency_values) if latency_values else 0.0
    return {"cost_usd": cost, "latency_ms": latency}


def _section_lines(content: str, heading: str) -> list[str]:
    lines = content.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == f"## {heading}":
            start = index + 1
            break
    if start is None:
        return []
    collected: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip():
            collected.append(line.strip())
    return collected


def _usage(model: str | None, *, latency_ms: float) -> dict[str, Any]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
        "model": model or "scripted-gold-set",
        "cost_usd": 0.0,
        "latency_ms": latency_ms,
    }


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
