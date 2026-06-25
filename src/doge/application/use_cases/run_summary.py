"""Build API-ready run summary, claim, citation, and eval views."""

from __future__ import annotations

import hashlib
from typing import Any

from doge.application.services.financial_eval_service import FinancialEvalService
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun, RunStatus
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.evidence_repository import IEvidenceRepository
from doge.shared.scope import TenantScope

_TERMINAL_STATUSES = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}


def _scope_for_summary(scope: TenantScope | None, tenant_id: str | None) -> TenantScope:
    if scope is None:
        return TenantScope.from_tenant_id(tenant_id)
    if tenant_id is not None and tenant_id != scope.tenant_id:
        raise ValueError(f"tenant mismatch for run summary: {tenant_id} != {scope.tenant_id}")
    return scope


class BuildRunSummary:
    """Assemble structured run-review resources from persisted runtime state."""

    def __init__(
        self,
        runtime: IResearchAgentRuntime,
        evidence_repository: IEvidenceRepository | None = None,
        eval_service: FinancialEvalService | None = None,
    ) -> None:
        self._runtime = runtime
        self._evidence_repository = evidence_repository
        self._eval_service = eval_service or FinancialEvalService()

    def build(
        self,
        run: AgentRun,
        *,
        scope: TenantScope | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_scope = _scope_for_summary(scope, tenant_id)
        events = self._runtime.list_events(resolved_scope, run.run_id)
        artifacts = self._runtime.list_artifacts(resolved_scope, run.run_id)
        evidence = self._list_evidence(run.run_id, scope=resolved_scope)
        artifact = _latest_artifact(artifacts)
        summary = _summary_for(run, artifact, events)
        claims = _claims_for(run, artifacts, evidence, summary["summary_id"])
        citations = _citations_for(run, artifacts, evidence, claims)
        evaluation = _eval_for(
            run,
            artifact,
            events,
            evidence,
            claims,
            citations,
            summary["summary_id"],
            self._eval_service,
        )
        return {
            "summary": summary,
            "claims": claims,
            "citations": citations,
            "eval": evaluation,
        }

    def _list_evidence(self, run_id: str, *, scope: TenantScope) -> list[Any]:
        if self._evidence_repository is None:
            return []
        return self._evidence_repository.list_evidence(scope=scope, run_id=run_id, limit=500)


def redact_inaccessible_citations(result: dict[str, Any], accessible_document_ids: set[str]) -> dict[str, Any]:
    """Hide snippets for citations whose document IDs failed ACL checks."""

    citations = []
    inaccessible = 0
    for citation in result["citations"]:
        redacted = dict(citation)
        document_id = redacted.get("document_id")
        if document_id and document_id not in accessible_document_ids:
            inaccessible += 1
            redacted["accessible"] = False
            redacted["snippet"] = ""
        citations.append(redacted)
    updated = dict(result)
    updated["citations"] = citations
    updated["eval"] = _recompute_access_eval(dict(result["eval"]), result["claims"], citations, inaccessible)
    return updated


def _summary_for(run: AgentRun, artifact: AgentArtifact | None, events: list[AgentEvent]) -> dict[str, Any]:
    status = "not_available"
    if artifact is not None:
        status = "current" if run.status in _TERMINAL_STATUSES else "draft"
    high_watermark = max((event.sequence for event in events), default=0)
    summary_text = artifact.content if artifact is not None else ""
    return {
        "summary_id": _stable_id("sum", run.run_id, str(high_watermark), summary_text[:512]),
        "run_id": run.run_id,
        "status": status,
        "run_status": run.status.value,
        "summary_text": summary_text,
        "source_artifact_id": artifact.artifact_id if artifact else None,
        "source_event_high_watermark": high_watermark,
        "created_at": artifact.created_at if artifact else run.updated_at,
        "updated_at": run.updated_at,
    }


def _claims_for(
    run: AgentRun,
    artifacts: list[AgentArtifact],
    evidence: list[Any],
    summary_id: str,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_text: set[str] = set()
    for artifact in artifacts:
        for raw in _list_field(artifact.data.get("claims")):
            text = str(raw.get("text") or raw.get("claim") or "").strip()
            if not text:
                continue
            claim_id = str(raw.get("claim_id") or _stable_id("clm", run.run_id, text))
            if claim_id in seen or text in seen_text:
                continue
            seen.add(claim_id)
            seen_text.add(text)
            claims.append(
                {
                    "claim_id": claim_id,
                    "summary_id": summary_id,
                    "run_id": run.run_id,
                    "claim_text": text,
                    "support_status": _support_status(str(raw.get("status") or raw.get("support_status") or "")),
                    "evidence_count": int(raw.get("evidence_count") or 0),
                    "source": "artifact",
                }
            )
    for item in evidence:
        claim_text = str(getattr(item, "claim", "") or "").strip()
        if not claim_text:
            continue
        claim_id = _stable_id("clm", run.run_id, claim_text)
        if claim_id in seen or claim_text in seen_text:
            continue
        seen.add(claim_id)
        seen_text.add(claim_text)
        claims.append(
            {
                "claim_id": claim_id,
                "summary_id": summary_id,
                "run_id": run.run_id,
                "claim_text": claim_text,
                "support_status": "supported",
                "evidence_count": 1,
                "source": "evidence",
            }
        )
    return claims


def _citations_for(
    run: AgentRun,
    artifacts: list[AgentArtifact],
    evidence: list[Any],
    claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    claim_by_text = {claim["claim_text"]: claim["claim_id"] for claim in claims}
    for artifact in artifacts:
        for raw in _list_field(artifact.data.get("citations")):
            citation = _citation_from_mapping(run.run_id, raw)
            if not citation or citation["citation_id"] in seen:
                continue
            seen.add(citation["citation_id"])
            citations.append(citation)
    for item in evidence:
        evidence_id = getattr(item, "evidence_id", "")
        claim_text = str(getattr(item, "claim", "") or "").strip()
        citation = {
            "citation_id": _stable_id("cit", run.run_id, evidence_id or getattr(item, "support_snippet", "")),
            "run_id": run.run_id,
            "claim_id": claim_by_text.get(claim_text),
            "evidence_id": evidence_id,
            "document_id": getattr(item, "document_id", None),
            "page_id": getattr(item, "page_id", None),
            "chunk_id": getattr(item, "chunk_id", None),
            "page_number": getattr(item, "page_number", None),
            "source": _source_label(item),
            "snippet": getattr(item, "support_snippet", "") or "",
            "snippet_hash": _hash_text(getattr(item, "support_snippet", "") or ""),
            "provider_file_id": _metadata(item).get("provider_file_id"),
            "accessible": True,
        }
        if citation["citation_id"] not in seen:
            seen.add(citation["citation_id"])
            citations.append(citation)
    return citations


def _eval_for(
    run: AgentRun,
    artifact: AgentArtifact | None,
    events: list[AgentEvent],
    evidence: list[Any],
    claims: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    summary_id: str,
    eval_service: FinancialEvalService,
) -> dict[str, Any]:
    evidence_dicts = [_evidence_to_dict(item) for item in evidence]
    quality = {}
    if artifact is not None:
        quality = eval_service.score_artifact(artifact.content, events, evidence_records=evidence_dicts)
    failed_checks = []
    unsupported = [claim for claim in claims if claim["support_status"] != "supported"]
    if unsupported:
        failed_checks.append("unsupported_claims")
    broken = [
        citation for citation in citations
        if citation.get("evidence_id") and citation["evidence_id"] not in {getattr(item, "evidence_id", "") for item in evidence}
    ]
    if broken:
        failed_checks.append("broken_evidence_reference")
    coverage_ratio = _coverage_ratio(claims, citations)
    if claims and coverage_ratio < 1.0:
        failed_checks.append("citation_coverage_incomplete")
    return {
        "eval_id": _stable_id("eval", run.run_id, summary_id),
        "run_id": run.run_id,
        "summary_id": summary_id,
        "coverage_ratio": coverage_ratio,
        "claim_count": len(claims),
        "supported_claim_count": len([claim for claim in claims if claim["support_status"] == "supported"]),
        "citation_count": len(citations),
        "accessible_citation_count": len([citation for citation in citations if citation.get("accessible", True)]),
        "failed_checks": failed_checks,
        "metrics": quality,
    }


def _recompute_access_eval(
    evaluation: dict[str, Any],
    claims: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    inaccessible_count: int,
) -> dict[str, Any]:
    evaluation["accessible_citation_count"] = len([citation for citation in citations if citation.get("accessible", True)])
    evaluation["coverage_ratio"] = _coverage_ratio(claims, citations)
    failed_checks = list(evaluation.get("failed_checks") or [])
    if inaccessible_count and "inaccessible_citations" not in failed_checks:
        failed_checks.append("inaccessible_citations")
    if claims and evaluation["coverage_ratio"] < 1.0 and "citation_coverage_incomplete" not in failed_checks:
        failed_checks.append("citation_coverage_incomplete")
    evaluation["failed_checks"] = failed_checks
    return evaluation


def _coverage_ratio(claims: list[dict[str, Any]], citations: list[dict[str, Any]]) -> float:
    if not claims:
        return 0.0
    cited_claims = {
        citation.get("claim_id")
        for citation in citations
        if citation.get("claim_id") and citation.get("accessible", True)
    }
    return len(cited_claims) / len(claims)


def _citation_from_mapping(run_id: str, raw: dict[str, Any]) -> dict[str, Any] | None:
    snippet = str(raw.get("snippet") or raw.get("support_snippet") or "")
    source = str(raw.get("source") or "")
    citation_id = str(raw.get("citation_id") or _stable_id("cit", run_id, source, snippet))
    if not source and not snippet and not raw.get("evidence_id"):
        return None
    return {
        "citation_id": citation_id,
        "run_id": run_id,
        "claim_id": raw.get("claim_id"),
        "evidence_id": raw.get("evidence_id"),
        "document_id": raw.get("document_id"),
        "page_id": raw.get("page_id"),
        "chunk_id": raw.get("chunk_id"),
        "page_number": raw.get("page_number"),
        "source": source,
        "snippet": snippet,
        "snippet_hash": str(raw.get("snippet_hash") or _hash_text(snippet)),
        "provider_file_id": raw.get("provider_file_id"),
        "accessible": bool(raw.get("accessible", True)),
    }


def _latest_artifact(artifacts: list[AgentArtifact]) -> AgentArtifact | None:
    return artifacts[-1] if artifacts else None


def _list_field(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _support_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"supported", "unsupported", "unverified", "conflicted"}:
        return normalized
    if normalized in {"contradicted", "contradiction"}:
        return "conflicted"
    if normalized in {"insufficient_evidence", "insufficient", "missing"}:
        return "unsupported"
    return "unverified"


def _source_label(item: Any) -> str:
    page_number = getattr(item, "page_number", None)
    document_id = getattr(item, "document_id", "")
    return f"{document_id} p.{page_number}" if page_number is not None else str(document_id)


def _metadata(item: Any) -> dict[str, Any]:
    metadata = getattr(item, "metadata", {}) or {}
    return metadata if isinstance(metadata, dict) else {}


def _evidence_to_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "to_dict"):
        return item.to_dict()
    return {}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
