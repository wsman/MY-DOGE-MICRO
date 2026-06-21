from doge.application.services.claim_validation_service import ClaimValidationService


def test_claim_validation_marks_supported_when_terms_match_evidence():
    result = ClaimValidationService().validate(
        report_id="report-1",
        claim_text="earnings quality improved",
        evidence_results=[{"text": "The report says earnings quality improved in Q2."}],
    )

    assert result.status == "supported"
    assert result.evidence_count == 1


def test_claim_validation_marks_insufficient_without_evidence():
    result = ClaimValidationService().validate(
        report_id="report-1",
        claim_text="rates are falling",
        evidence_results=[],
    )

    assert result.status == "insufficient_evidence"
    assert result.evidence_count == 0


def test_claim_validation_requires_numeric_support_for_numeric_claim():
    supported = ClaimValidationService().validate(
        report_id="report-1",
        claim_text="ranking score is 2.1",
        evidence_results=[{"text": "The ranking score is 2.1 for the leader."}],
    )
    insufficient = ClaimValidationService().validate(
        report_id="report-1",
        claim_text="ranking score is 3.7",
        evidence_results=[{"text": "The ranking score is 2.1 for the leader."}],
    )

    assert supported.status == "supported"
    assert insufficient.status == "insufficient_evidence"
