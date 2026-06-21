from doge.application.services.citation_service import CitationService
from doge.core.domain.claim_models import ClaimRecord


def test_citation_service_builds_source_citations_from_rag_results():
    claim = ClaimRecord.create(
        report_id="industry-us-semiconductor-demo",
        text="NVDA leads the semiconductor ranking.",
        status="supported",
        evidence_count=1,
    )
    results = [
        {
            "document_id": "doc-1",
            "page_number": 3,
            "chunk_id": "chk-1",
            "text": "NVDA leads the semiconductor ranking with strong accelerator demand.",
            "score": 0.91,
            "visibility": "local",
        }
    ]

    citations = CitationService().citations_for_claim(claim, results)

    assert len(citations) == 1
    assert citations[0].claim_id == claim.claim_id
    assert citations[0].source == "doc-1 p.3"
    assert citations[0].page_number == 3
    assert "accelerator demand" in citations[0].snippet


def test_citation_service_renders_empty_markdown():
    assert CitationService().render_markdown([]) == "- No source citations available."
