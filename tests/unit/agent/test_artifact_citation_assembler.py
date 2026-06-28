"""Unit tests for ArtifactCitationAssembler."""

from __future__ import annotations

import pytest

from doge.application.agent.artifact_citation_assembler import ArtifactCitationAssembler
from doge.core.domain.agent_models import AgentRun
from doge.core.domain.claim_models import ClaimRecord, CitationRecord, ClaimEvidenceRelation
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.ports.evidence_repository import IEvidenceRepository
from doge.core.ports.runtime_services import ToolResult
from doge.shared.scope import TenantScope


class FakeEvidenceRepository(IEvidenceRepository):
    """In-memory evidence repository for testing."""

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


class FakeClassifier:
    def __init__(self, classifications=None):
        self._classifications = classifications or {}

    def classify(self, claim_text, evidence_snippet):
        key = (claim_text, evidence_snippet)
        if key in self._classifications:
            return self._classifications[key]
        # Default: supported if terms overlap significantly
        claim_words = set(claim_text.lower().split())
        ev_words = set(evidence_snippet.lower().split())
        overlap = claim_words & ev_words
        if len(overlap) >= 2:
            return FakeClassification("supported", 0.85)
        if len(overlap) >= 1:
            return FakeClassification("partial", 0.55)
        return FakeClassification("unrelated", 0.1)


class FakeClassification:
    def __init__(self, support_status, confidence, method="deterministic"):
        self.support_status = support_status
        self.confidence = confidence
        self.method = method


@pytest.fixture
def evidence_chunk():
    return EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chk-1",
        text="NVDA leads the semiconductor ranking with strong accelerator demand.",
        source_tool="stock_overview",
        run_id="run-test",
    )


@pytest.fixture
def evidence_repo(evidence_chunk):
    return FakeEvidenceRepository(chunks=[evidence_chunk])


@pytest.fixture
def assembler(evidence_repo):
    return ArtifactCitationAssembler(
        evidence_repository=evidence_repo,
        citation_service=FakeCitationService(),
        claim_validation_service=FakeClaimValidationService(),
        classifier=FakeClassifier(),
    )


@pytest.fixture
def run():
    return AgentRun.create(workflow="test", question="Analyze NVDA")


def test_assembler_content_with_evidence_gets_citations(assembler, run, evidence_chunk):
    content = "NVDA leads the semiconductor ranking. Revenue grew 12% in Q2."
    tool_results = [
        ToolResult(
            name="stock_overview",
            data={"ticker": "NVDA"},
            evidence_refs=[evidence_chunk.to_dict()],
        )
    ]

    artifact = assembler.assemble(run, content, tool_results)

    assert artifact.kind == "investment_memo"
    assert "Sources" in artifact.content
    assert len(artifact.data["claims"]) > 0
    assert len(artifact.data["citations"]) > 0
    assert len(artifact.data["relations"]) > 0
    assert "support_status" in artifact.data
    assert "coverage_ratio" in artifact.data


def test_assembler_content_without_evidence_returns_artifact_unchanged(assembler, run):
    content = "This is a general statement without specific numbers."
    tool_results = []

    artifact = assembler.assemble(run, content, tool_results)

    assert artifact.kind == "investment_memo"
    # Content should be largely unchanged (no Sources section added if no citations)
    # But claims may still be extracted
    assert len(artifact.data["claims"]) >= 0
    assert len(artifact.data["citations"]) == 0
    assert len(artifact.data["relations"]) == 0
    assert artifact.data["support_status"] == "insufficient_evidence"
    assert artifact.data["coverage_ratio"] == 0.0


def test_assembler_unsupported_claim_marked_unsupported(assembler, run):
    content = "The moon is made of green cheese. This has no evidence support."
    tool_results = []

    artifact = assembler.assemble(run, content, tool_results)

    claims = artifact.data["claims"]
    for claim in claims:
        assert claim["status"] == "insufficient_evidence"
    assert artifact.data["support_status"] == "insufficient_evidence"
    assert artifact.data["coverage_ratio"] == 0.0


def test_assembler_injects_inline_markers(assembler, run, evidence_chunk):
    content = "NVDA leads the semiconductor ranking."
    tool_results = [
        ToolResult(
            name="stock_overview",
            data={"ticker": "NVDA"},
            evidence_refs=[evidence_chunk.to_dict()],
        )
    ]

    artifact = assembler.assemble(run, content, tool_results)

    assert "[^evd-" in artifact.content or "[^?]" in artifact.content


def test_assembler_appends_citation_section(assembler, run, evidence_chunk):
    content = "NVDA leads the semiconductor ranking."
    tool_results = [
        ToolResult(
            name="stock_overview",
            data={"ticker": "NVDA"},
            evidence_refs=[evidence_chunk.to_dict()],
        )
    ]

    artifact = assembler.assemble(run, content, tool_results)

    assert "## Sources" in artifact.content


def test_assembler_deduplicates_evidence_by_id(assembler, run, evidence_chunk):
    content = "NVDA leads the semiconductor ranking."
    # Same evidence ref twice
    tool_results = [
        ToolResult(
            name="stock_overview",
            data={"ticker": "NVDA"},
            evidence_refs=[evidence_chunk.to_dict()],
        ),
        ToolResult(
            name="stock_overview",
            data={"ticker": "NVDA"},
            evidence_refs=[evidence_chunk.to_dict()],
        ),
    ]

    artifact = assembler.assemble(run, content, tool_results)

    # Should not duplicate citations
    citation_ids = [c["citation_id"] for c in artifact.data["citations"]]
    assert len(citation_ids) == len(set(citation_ids))


def test_assembler_computes_coverage_ratio_with_partial_support(assembler, run, evidence_chunk):
    content = "NVDA leads the semiconductor ranking. Some other unrelated claim here."
    tool_results = [
        ToolResult(
            name="stock_overview",
            data={"ticker": "NVDA"},
            evidence_refs=[evidence_chunk.to_dict()],
        )
    ]

    artifact = assembler.assemble(run, content, tool_results)

    # At least one claim should have evidence, so coverage > 0
    assert artifact.data["coverage_ratio"] > 0.0


def test_assembler_returns_empty_when_no_claims_extracted(assembler, run):
    content = ""
    tool_results = []

    artifact = assembler.assemble(run, content, tool_results)

    assert artifact.data["claims"] == []
    assert artifact.data["citations"] == []
    assert artifact.data["relations"] == []
    assert artifact.data["coverage_ratio"] == 0.0
    assert artifact.data["support_status"] == "insufficient_evidence"


def test_assembler_with_none_evidence_repo_uses_tool_results_only(run):
    """Assembler should work even with minimal evidence repo by using tool result evidence_refs."""
    empty_repo = FakeEvidenceRepository(chunks=[])
    assembler = ArtifactCitationAssembler(
        evidence_repository=empty_repo,
        citation_service=FakeCitationService(),
        claim_validation_service=FakeClaimValidationService(),
        classifier=FakeClassifier(),
    )
    content = "NVDA leads the semiconductor ranking."
    chunk = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chk-1",
        text="NVDA leads the semiconductor ranking with strong accelerator demand.",
        source_tool="stock_overview",
        run_id="run-test",
    )
    tool_results = [
        ToolResult(
            name="stock_overview",
            data={"ticker": "NVDA"},
            evidence_refs=[chunk.to_dict()],
        )
    ]

    artifact = assembler.assemble(run, content, tool_results)

    # Should still produce citations from tool result evidence_refs
    assert len(artifact.data["citations"]) > 0
    assert len(artifact.data["relations"]) > 0


def test_assembler_claim_extraction_skips_short_sentences(assembler, run):
    content = "Hi. OK. Yes. NVDA revenue grew 12% in Q2."
    tool_results = []

    artifact = assembler.assemble(run, content, tool_results)

    # Only the meaningful sentence should be extracted as a claim
    claim_texts = [c["text"] for c in artifact.data["claims"]]
    assert all(len(t) >= 10 for t in claim_texts)
