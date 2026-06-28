from doge.application.services.citation_support_classifier import CitationSupportClassifier


def test_classifier_marks_number_and_term_match_supported():
    result = CitationSupportClassifier().classify(
        "Revenue grew 12%.",
        "The filing says revenue grew 12% year over year.",
    )

    assert result.support_status == "supported"
    assert result.confidence > 0.6


def test_classifier_marks_partial_overlap_partial():
    result = CitationSupportClassifier().classify(
        "Revenue grew 12%.",
        "Revenue increased but the percentage was not disclosed.",
    )

    assert result.support_status == "partial"


def test_classifier_marks_unrelated_snippet_unrelated():
    result = CitationSupportClassifier().classify(
        "Revenue grew 12%.",
        "The board appointed a new independent director.",
    )

    assert result.support_status == "unrelated"


def test_classifier_marks_conflicting_number_contradicted():
    result = CitationSupportClassifier().classify(
        "Revenue grew 12%.",
        "Revenue grew 3% year over year.",
    )

    assert result.support_status == "contradicted"
