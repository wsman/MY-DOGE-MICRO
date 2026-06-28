"""Citation precision benchmark for Sprint B.

Deterministic benchmark that measures:
- citation_precision: fraction of claims with at least one citation
- citation_recall: fraction of evidence chunks that are cited
- support_status distribution: counts of supported/partial/insufficient_evidence

Runs without live providers using in-memory fakes.
"""

from __future__ import annotations

from typing import Any

from doge.application.agent.artifact_citation_assembler import ArtifactCitationAssembler
from doge.core.domain.agent_models import AgentRun
from doge.core.domain.claim_models import ClaimRecord, CitationRecord, ClaimEvidenceRelation
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.ports.evidence_repository import IEvidenceRepository
from doge.core.ports.runtime_services import ToolResult
from doge.shared.scope import TenantScope


class FakeEvidenceRepository(IEvidenceRepository):
    """In-memory evidence repository for benchmark use."""

    def __init__(self, chunks: list[EvidenceChunk] | None = None):
        self._chunks = chunks or []

    def save_page(self, page, scope):
        pass

    def list_pages(self, document_id, scope):
        return []

    def save_chunk(self, chunk, scope):
        pass

    def list_chunks(self, scope, document_ids=None, limit=20):
        return []

    def get_chunk(self, chunk_id, scope):
        return None

    def list_chunks_for_run(self, run_id, scope):
        return []

    def save_evidence(self, evidence, scope):
        pass

    def get_evidence(self, evidence_id, scope):
        return None

    def list_evidence(self, *, scope, run_id=None, document_id=None, limit=20):
        return []

    def list_evidence_chunks(self, *, scope, run_id=None, evidence_ids=None, limit=100):
        if run_id is not None:
            return [c for c in self._chunks if c.run_id == run_id][:limit]
        if evidence_ids is not None:
            return [c for c in self._chunks if c.evidence_id in evidence_ids][:limit]
        return self._chunks[:limit]


class FakeCitationService:
    def citations_for_claim(self, claim, evidence_results, *, limit=3, context=None):
        citations = []
        for item in evidence_results[:limit]:
            snippet = str(item.get("text") or item.get("support_snippet") or "")[:500]
            if not snippet:
                continue
            citations.append(
                CitationRecord.create(
                    claim_id=claim.claim_id,
                    report_id=claim.report_id,
                    source=item.get("source", "local evidence"),
                    snippet=snippet,
                    document_id=item.get("document_id"),
                    page_number=item.get("page_number"),
                    chunk_id=item.get("chunk_id"),
                    evidence_id=item.get("evidence_id"),
                )
            )
        return citations

    def render_markdown(self, citations):
        if not citations:
            return "- No source citations available."
        lines = []
        for index, citation in enumerate(citations, start=1):
            page = f", p. {citation.page_number}" if citation.page_number is not None else ""
            lines.append(f"- [{index}] {citation.source}{page}: {citation.snippet}")
        return "\n".join(lines)


class FakeClaimValidationService:
    def validate(self, *, report_id, claim_text, evidence_results, metadata=None):
        if not evidence_results:
            status = "insufficient_evidence"
        else:
            status = "supported"
        return ClaimRecord.create(
            report_id=report_id,
            text=claim_text,
            status=status,
            evidence_count=len(evidence_results),
            metadata=metadata or {},
        )


class FakeClassification:
    def __init__(self, support_status, confidence, method="deterministic"):
        self.support_status = support_status
        self.confidence = confidence
        self.method = method


class FakeClassifier:
    """Deterministic classifier for benchmark use."""

    def __init__(self, classifications=None):
        self._classifications = classifications or {}

    def classify(self, claim_text, evidence_snippet):
        key = (claim_text, evidence_snippet)
        if key in self._classifications:
            return self._classifications[key]
        # Deterministic default: supported if significant term overlap
        claim_words = set(claim_text.lower().split())
        ev_words = set(evidence_snippet.lower().split())
        overlap = claim_words & ev_words
        if len(overlap) >= 2:
            return FakeClassification("supported", 0.85)
        if len(overlap) >= 1:
            return FakeClassification("partial", 0.55)
        return FakeClassification("unrelated", 0.1)


def build_benchmark_assembler(evidence_chunks: list[EvidenceChunk]) -> ArtifactCitationAssembler:
    """Build an ArtifactCitationAssembler with fake dependencies for benchmarking."""
    return ArtifactCitationAssembler(
        evidence_repository=FakeEvidenceRepository(chunks=evidence_chunks),
        citation_service=FakeCitationService(),
        claim_validation_service=FakeClaimValidationService(),
        classifier=FakeClassifier(),
    )


def run_citation_precision_benchmark(
    content: str,
    evidence_chunks: list[EvidenceChunk],
    tool_results: list[ToolResult] | None = None,
) -> dict[str, Any]:
    """Run the citation precision benchmark on a deterministic fixture.

    Returns a dict with:
    - citation_precision: fraction of claims with at least one citation
    - citation_recall: fraction of evidence chunks that are cited
    - support_status_distribution: counts per status
    - claim_count: total claims extracted
    - cited_claim_count: claims with at least one citation
    - evidence_chunk_count: total evidence chunks available
    - cited_evidence_count: unique evidence chunks cited
    - coverage_ratio: fraction of claims with any relation (from assembler)
    - support_status: overall support status from assembler
    - passed_thresholds: bool indicating whether thresholds were met
    """
    run = AgentRun.create(workflow="benchmark", question="Benchmark run", run_id="run-benchmark")
    assembler = build_benchmark_assembler(evidence_chunks)
    artifact = assembler.assemble(run, content, tool_results or [])

    claims = artifact.data.get("claims", [])
    citations = artifact.data.get("citations", [])
    relations = artifact.data.get("relations", [])

    claim_count = len(claims)
    cited_claim_ids = {c["claim_id"] for c in citations if c.get("claim_id")}
    cited_claim_count = len(cited_claim_ids)
    citation_precision = cited_claim_count / claim_count if claim_count else 0.0

    evidence_chunk_count = len(evidence_chunks)
    cited_evidence_ids = {c["evidence_id"] for c in citations if c.get("evidence_id")}
    cited_evidence_count = len(cited_evidence_ids)
    citation_recall = cited_evidence_count / evidence_chunk_count if evidence_chunk_count else 0.0

    support_status_distribution = {"supported": 0, "partial": 0, "insufficient_evidence": 0, "unrelated": 0, "contradicted": 0}
    for claim in claims:
        status = claim.get("status", "insufficient_evidence")
        if status in support_status_distribution:
            support_status_distribution[status] += 1
        else:
            support_status_distribution["insufficient_evidence"] += 1

    # Threshold checks
    supported_claims = [c for c in claims if c.get("status") == "supported"]
    supported_cited = sum(1 for c in supported_claims if c.get("claim_id") in cited_claim_ids)
    supported_precision = supported_cited / len(supported_claims) if supported_claims else 1.0

    passed_thresholds = supported_precision >= 0.8

    return {
        "citation_precision": citation_precision,
        "citation_recall": citation_recall,
        "support_status_distribution": support_status_distribution,
        "claim_count": claim_count,
        "cited_claim_count": cited_claim_count,
        "evidence_chunk_count": evidence_chunk_count,
        "cited_evidence_count": cited_evidence_count,
        "coverage_ratio": artifact.data.get("coverage_ratio", 0.0),
        "support_status": artifact.data.get("support_status", "insufficient_evidence"),
        "supported_precision": supported_precision,
        "passed_thresholds": passed_thresholds,
    }


def benchmark_supported_claim_with_evidence() -> dict[str, Any]:
    """Gold-set case: a supported claim with matching evidence."""
    content = "NVDA revenue grew 126% in fiscal year 2025."
    evidence = [
        EvidenceChunk.create(
            document_id="doc-ar-nvda",
            page_number=42,
            chunk_id="chk-revenue",
            text="NVDA revenue grew 126% year over year in fiscal 2025.",
            source_tool="annual_report",
            run_id="run-benchmark",
        ),
    ]
    return run_citation_precision_benchmark(content, evidence)


def benchmark_unsupported_claim_without_evidence() -> dict[str, Any]:
    """Gold-set case: an unsupported claim with no matching evidence."""
    content = "The company guaranteed a 20% dividend increase next quarter."
    evidence = [
        EvidenceChunk.create(
            document_id="doc-ar-aapl",
            page_number=10,
            chunk_id="chk-cash",
            text="Cash and cash equivalents totaled 28.4 billion at year end.",
            source_tool="annual_report",
            run_id="run-benchmark",
        ),
    ]
    return run_citation_precision_benchmark(content, evidence)


def benchmark_mixed_claims_partial_coverage() -> dict[str, Any]:
    """Gold-set case: multiple claims where only some have evidence."""
    content = (
        "NVDA revenue grew 126% in fiscal year 2025. "
        "The company guaranteed a 20% dividend increase next quarter."
    )
    evidence = [
        EvidenceChunk.create(
            document_id="doc-ar-nvda",
            page_number=42,
            chunk_id="chk-revenue",
            text="NVDA revenue grew 126% year over year in fiscal 2025.",
            source_tool="annual_report",
            run_id="run-benchmark",
        ),
    ]
    return run_citation_precision_benchmark(content, evidence)


def run_all_benchmarks() -> dict[str, Any]:
    """Run all benchmark cases and return aggregated results."""
    results = {
        "supported_with_evidence": benchmark_supported_claim_with_evidence(),
        "unsupported_without_evidence": benchmark_unsupported_claim_without_evidence(),
        "mixed_partial_coverage": benchmark_mixed_claims_partial_coverage(),
    }

    avg_precision = sum(r["citation_precision"] for r in results.values()) / len(results)
    avg_recall = sum(r["citation_recall"] for r in results.values()) / len(results)
    all_passed = all(r["passed_thresholds"] for r in results.values())

    return {
        "benchmarks": results,
        "aggregated": {
            "avg_citation_precision": avg_precision,
            "avg_citation_recall": avg_recall,
            "all_thresholds_passed": all_passed,
            "case_count": len(results),
        },
    }
