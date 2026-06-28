from doge.core.domain.claim_models import CitationRecord, ClaimEvidenceRelation, ClaimRecord
from doge.infrastructure.database.claim_repository import SQLiteClaimRepository


def test_sqlite_claim_repository_persists_claims_and_citations(tmp_path):
    repo = SQLiteClaimRepository(tmp_path / "agent.db")
    claim = ClaimRecord.create(
        report_id="report-1",
        text="NVDA leads the ranking.",
        status="supported",
        evidence_count=1,
    )
    citation = CitationRecord.create(
        report_id=claim.report_id,
        claim_id=claim.claim_id,
        source="doc-1 p.2",
        snippet="NVDA leads the ranking.",
        document_id="doc-1",
        page_number=2,
        chunk_id="chk-1",
    )

    repo.save_claim(claim)
    repo.save_citation(citation)

    assert repo.list_claims("report-1") == [claim]
    citations = repo.list_citations(report_id="report-1")
    assert len(citations) == 1
    assert citations[0].snippet == "NVDA leads the ranking."
    assert repo.list_citations(claim_id=claim.claim_id)[0].document_id == "doc-1"


def test_sqlite_claim_repository_persists_claim_evidence_relations(tmp_path):
    repo = SQLiteClaimRepository(tmp_path / "agent.db")
    relation = ClaimEvidenceRelation.create(
        claim_id="claim-1",
        evidence_id="evd-1",
        support_status="supported",
        confidence=0.92,
        method="deterministic-test",
        metadata={"reason": "number_match"},
    )

    repo.save_relation(relation)

    assert repo.list_relations_for_claim("claim-1") == [relation]
    by_evidence = repo.list_relations_for_evidence("evd-1")
    assert by_evidence[0].claim_id == "claim-1"
    assert by_evidence[0].metadata == {"reason": "number_match"}
