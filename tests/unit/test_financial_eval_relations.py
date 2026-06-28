from doge.application.services.financial_eval_service import FinancialEvalService


def test_financial_eval_scores_claim_evidence_relations():
    service = FinancialEvalService()
    claims = [
        {"claim_id": "claim-1", "claim_text": "Revenue grew 12%."},
        {"claim_id": "claim-2", "claim_text": "Margin doubled."},
    ]
    citations = [
        {"claim_id": "claim-1", "evidence_id": "evd-1", "snippet": "Revenue grew 12% year over year."},
        {"claim_id": "claim-2", "evidence_id": "evd-2", "snippet": "The board changed its charter."},
    ]
    evidence = [
        {"evidence_id": "evd-1", "support_snippet": "Revenue grew 12% year over year."},
        {"evidence_id": "evd-2", "support_snippet": "The board changed its charter."},
    ]

    result = service.score_claim_evidence_relations(claims, citations, evidence)

    assert result["claim_evidence_relation_count"] == 2
    assert result["supported_relation_count"] == 1
    assert result["unrelated_relation_count"] == 1
    assert result["classification_confidence_avg"] is not None
