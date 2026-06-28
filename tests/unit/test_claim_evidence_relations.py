from doge.core.domain.claim_models import ClaimEvidenceRelation


def test_claim_evidence_relation_create_normalizes_status_and_confidence():
    relation = ClaimEvidenceRelation.create(
        claim_id="claim-1",
        evidence_id="evd-1",
        support_status="conflicted",
        confidence=1.4,
    )

    assert relation.support_status == "contradicted"
    assert relation.confidence == 1.0
    assert relation.relation_id.startswith("rel-")


def test_claim_evidence_relation_round_trips_mapping_metadata():
    relation = ClaimEvidenceRelation.from_mapping(
        {
            "relation_id": "rel-1",
            "claim_id": "claim-1",
            "evidence_id": "evd-1",
            "support_status": "partial",
            "confidence": 0.5,
            "method": "deterministic",
            "metadata": '{"reason": "term_overlap"}',
            "created_at": "2026-06-28T00:00:00+00:00",
        }
    )

    assert relation.to_dict()["metadata"] == {"reason": "term_overlap"}
