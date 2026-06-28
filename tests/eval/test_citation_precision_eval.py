"""Pytest test runner for citation precision benchmark.

Runs the deterministic benchmark as normal pytest cases and asserts thresholds.
"""

from __future__ import annotations

import pytest

from tests.benchmark.test_citation_precision_benchmark import (
    benchmark_mixed_claims_partial_coverage,
    benchmark_supported_claim_with_evidence,
    benchmark_unsupported_claim_without_evidence,
    run_all_benchmarks,
)


def test_benchmark_supported_claim_with_evidence_meets_precision_threshold():
    """Supported claim with evidence should have citation_precision >= 0.8."""
    result = benchmark_supported_claim_with_evidence()

    assert result["claim_count"] >= 1
    assert result["cited_claim_count"] >= 1
    assert result["citation_precision"] >= 0.8
    assert result["citation_recall"] >= 0.8
    assert result["support_status"] == "supported"
    assert result["passed_thresholds"] is True


def test_benchmark_unsupported_claim_without_evidence_has_zero_precision():
    """Unsupported claim without evidence should have citation_precision == 0.0."""
    result = benchmark_unsupported_claim_without_evidence()

    assert result["claim_count"] >= 1
    assert result["cited_claim_count"] == 0
    assert result["citation_precision"] == 0.0
    assert result["citation_recall"] == 0.0
    assert result["support_status"] == "insufficient_evidence"


def test_benchmark_mixed_claims_partial_coverage():
    """Mixed claims should have partial support status and intermediate precision."""
    result = benchmark_mixed_claims_partial_coverage()

    assert result["claim_count"] >= 2
    assert result["cited_claim_count"] >= 1
    assert 0.0 < result["citation_precision"] < 1.0
    assert result["support_status"] == "partial"
    assert result["support_status_distribution"]["supported"] >= 1
    assert result["support_status_distribution"]["insufficient_evidence"] >= 1


def test_benchmark_aggregated_all_thresholds_passed():
    """All benchmark cases should pass their thresholds."""
    result = run_all_benchmarks()

    assert result["aggregated"]["all_thresholds_passed"] is True
    assert result["aggregated"]["avg_citation_precision"] >= 0.5
    assert result["aggregated"]["case_count"] == 3


def test_benchmark_support_status_distribution_has_expected_keys():
    """Support status distribution should include all expected statuses."""
    result = benchmark_supported_claim_with_evidence()
    dist = result["support_status_distribution"]

    assert "supported" in dist
    assert "partial" in dist
    assert "insufficient_evidence" in dist
    assert "unrelated" in dist
    assert "contradicted" in dist
