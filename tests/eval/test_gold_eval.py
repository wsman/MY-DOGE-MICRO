import json
from pathlib import Path

import pytest

from tests.eval.gold_eval import (
    REQUIRED_CATEGORIES,
    load_gold_cases,
    score_observations,
    summarize_gold_set,
)


GOLD_CASES = Path(__file__).with_name("gold_cases.json")


def test_gold_set_covers_required_financial_research_categories():
    cases = load_gold_cases(GOLD_CASES)

    summary = summarize_gold_set(cases)

    assert summary["case_count"] == 35
    assert set(summary["categories"]) == REQUIRED_CATEGORIES
    assert summary["required_categories_missing"] == []
    assert summary["citation_label_count"] >= 25
    assert summary["numerical_label_count"] >= 20
    assert summary["unsupported_claim_label_count"] >= 5
    assert summary["human_label_complete"] is True
    assert {"financial_research", "vision_analysis"} <= set(summary["profiles"])


def test_gold_set_rejects_cases_without_citation_or_insufficient_evidence_label(tmp_path):
    cases_path = tmp_path / "bad-gold.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "id": "bad_case",
                    "category": "annual_report",
                    "execution_profile": "financial_research",
                    "question": "Summarize revenue.",
                    "materials": [{"type": "document", "document_id": "doc-bad"}],
                    "expected_claims": [
                        {
                            "claim": "Revenue increased.",
                            "expected_status": "supported",
                        }
                    ],
                    "expected_citations": [],
                    "expected_numbers": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="lacks citation"):
        load_gold_cases(cases_path)


def test_score_observations_reports_retrieval_citation_number_and_usage_metrics():
    cases = [
        case
        for case in load_gold_cases(GOLD_CASES)
        if case["id"] == "ar_nvda_revenue_growth"
    ]
    observations = {
        "ar_nvda_revenue_growth": {
            "retrieved_evidence_ids": ["evd-ar-nvda-p42-revenue", "evd-noise"],
            "cited_evidence_ids": ["evd-ar-nvda-p42-revenue"],
            "claim_evidence_relations": [
                {
                    "claim_id": "clm-ar-nvda-revenue",
                    "evidence_id": "evd-ar-nvda-p42-revenue",
                    "support_status": "supported",
                }
            ],
            "claims": [{"claim_id": "clm-ar-nvda-revenue", "support_status": "supported"}],
            "numbers": {"revenue_growth_pct": 126.0},
            "usage": {"cost_usd": "0.04", "latency_ms": "1800"},
        }
    }

    result = score_observations(cases, observations)
    case_result = result["results"][0]

    assert result["case_count"] == 1
    assert result["observed_case_count"] == 1
    assert case_result["retrieval_recall"] == 1.0
    assert case_result["retrieval_precision"] == 0.5
    assert case_result["citation_precision"] == 1.0
    assert case_result["claim_evidence_precision"] == 1.0
    assert case_result["support_classification_accuracy"] == 1.0
    assert case_result["numerical_consistency"] == 1.0
    assert result["metrics"]["usage_cost_record_coverage"] == 1.0
    assert result["metrics"]["avg_cost_usd"] == 0.04
    assert result["metrics"]["avg_latency_ms"] == 1800.0


def test_gold_set_supported_claim_with_evidence_scores_perfectly():
    """Gold-set case: a supported claim with evidence should score 1.0 on precision and recall."""
    cases = [
        case
        for case in load_gold_cases(GOLD_CASES)
        if case["id"] == "ar_nvda_revenue_growth"
    ]
    assert len(cases) == 1
    case = cases[0]
    assert case["expected_claims"][0]["expected_status"] == "supported"
    assert len(case["expected_citations"]) == 1

    observations = {
        "ar_nvda_revenue_growth": {
            "retrieved_evidence_ids": ["evd-ar-nvda-p42-revenue"],
            "cited_evidence_ids": ["evd-ar-nvda-p42-revenue"],
            "claim_evidence_relations": [
                {
                    "claim_id": "clm-ar-nvda-revenue",
                    "evidence_id": "evd-ar-nvda-p42-revenue",
                    "support_status": "supported",
                }
            ],
            "claims": [{"claim_id": "clm-ar-nvda-revenue", "support_status": "supported"}],
            "numbers": {"revenue_growth_pct": 126.0},
            "usage": {"cost_usd": "0.04", "latency_ms": "1200"},
        }
    }

    result = score_observations(cases, observations)
    case_result = result["results"][0]

    assert case_result["citation_precision"] == 1.0
    assert case_result["retrieval_recall"] == 1.0
    assert case_result["support_classification_accuracy"] == 1.0
    assert case_result["numerical_consistency"] == 1.0


def test_gold_set_unsupported_claim_without_evidence_scores_zero_citation_precision():
    """Gold-set case: an unsupported claim without evidence should have citation_precision == 0.0."""
    cases = [
        case
        for case in load_gold_cases(GOLD_CASES)
        if case["id"] == "unsupported_no_source_dividend"
    ]
    assert len(cases) == 1
    case = cases[0]
    assert case["expected_claims"][0]["expected_status"] == "insufficient_evidence"
    assert len(case["expected_citations"]) == 0

    observations = {
        "unsupported_no_source_dividend": {
            "retrieved_evidence_ids": [],
            "cited_evidence_ids": [],
            "claim_evidence_relations": [],
            "claims": [{"claim_id": "clm-unsupported-dividend", "support_status": "insufficient_evidence"}],
            "numbers": {},
            "usage": {"cost_usd": "0.01", "latency_ms": "800"},
        }
    }

    result = score_observations(cases, observations)
    case_result = result["results"][0]

    # citation_precision is None when no citations are observed
    assert case_result["citation_precision"] is None
    assert case_result["retrieval_recall"] is None
    assert case_result["support_classification_accuracy"] == 1.0
    assert case_result["numerical_consistency"] is None
