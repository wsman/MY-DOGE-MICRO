from doge.application.services.citation_service import CitationService
from doge.core.domain.enterprise_context import EnterpriseContext
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


def test_citation_service_filters_enterprise_context_by_document_acl():
    claim = ClaimRecord.create(
        report_id="report-1",
        text="Only one document is allowed.",
        status="supported",
        evidence_count=2,
    )
    context = EnterpriseContext(
        tenant_id="tenant-a",
        user_hash="user-a",
        document_acl=frozenset({"doc-allowed"}),
    )

    citations = CitationService().citations_for_claim(
        claim,
        [
            {"document_id": "doc-allowed", "page_number": 1, "text": "allowed"},
            {"document_id": "doc-denied", "page_number": 2, "text": "denied"},
            {"chunk_id": "chk-unscoped", "text": "unscoped"},
        ],
        context=context,
    )

    assert len(citations) == 1
    assert citations[0].document_id == "doc-allowed"


def test_citation_service_denies_enterprise_context_without_document_acl():
    claim = ClaimRecord.create(
        report_id="report-1",
        text="No document ACL.",
        status="supported",
        evidence_count=1,
    )
    context = EnterpriseContext(tenant_id="tenant-a", user_hash="user-a")

    citations = CitationService().citations_for_claim(
        claim,
        [{"document_id": "doc-denied", "page_number": 2, "text": "denied"}],
        context=context,
    )

    assert citations == []


def test_citation_service_renders_empty_markdown():
    assert CitationService().render_markdown([]) == "- No source citations available."


def test_citation_precision_scores_real_evidence_ids():
    score = CitationService().citation_precision_score(
        "Claim cites evd-abc and evd-missing.",
        [{"evidence_id": "evd-abc"}],
    )

    assert score == 0.5
