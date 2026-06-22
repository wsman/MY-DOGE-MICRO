"""Offline gold-set quality checks for financial research cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_CATEGORIES = {
    "annual_report",
    "presentation",
    "chart_image",
    "portfolio_csv",
    "unsupported_claim",
    "multi_turn",
}


def load_gold_cases(path: Path) -> list[dict[str, Any]]:
    """Load and validate a financial research gold set."""

    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("gold cases file must contain a list")
    for index, case in enumerate(cases):
        _validate_case(case, index)
    return cases


def summarize_gold_set(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Return coverage and label-completeness metadata for a gold set."""

    categories = sorted({case["category"] for case in cases})
    profiles = sorted({case["execution_profile"] for case in cases})
    citation_labels = sum(len(case.get("expected_citations", [])) for case in cases)
    numerical_labels = sum(len(case.get("expected_numbers", [])) for case in cases)
    unsupported_labels = sum(
        1
        for case in cases
        for claim in case.get("expected_claims", [])
        if claim.get("expected_status") == "insufficient_evidence"
    )
    return {
        "case_count": len(cases),
        "categories": categories,
        "profiles": profiles,
        "required_categories_present": sorted(REQUIRED_CATEGORIES & set(categories)),
        "required_categories_missing": sorted(REQUIRED_CATEGORIES - set(categories)),
        "citation_label_count": citation_labels,
        "numerical_label_count": numerical_labels,
        "unsupported_claim_label_count": unsupported_labels,
        "human_label_complete": all(_case_has_human_label(case) for case in cases),
    }


def score_observations(cases: list[dict[str, Any]], observations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Score model/run observations against labeled gold cases.

    Observation shape is intentionally simple so CI, manual eval notebooks, or
    future runtime harnesses can write it:

    {
      "case-id": {
        "retrieved_evidence_ids": ["evd-a"],
        "cited_evidence_ids": ["evd-a"],
        "numbers": {"revenue": 100.0},
        "usage": {"cost_usd": 0.01, "latency_ms": 1200}
      }
    }
    """

    per_case = []
    for case in cases:
        observed = observations.get(case["id"], {})
        per_case.append(_score_case(case, observed))
    return {
        "case_count": len(cases),
        "observed_case_count": sum(1 for item in per_case if item["observed"]),
        "results": per_case,
        "metrics": {
            "retrieval_recall": _average_metric(per_case, "retrieval_recall"),
            "retrieval_precision": _average_metric(per_case, "retrieval_precision"),
            "citation_precision": _average_metric(per_case, "citation_precision"),
            "numerical_consistency": _average_metric(per_case, "numerical_consistency"),
            "usage_cost_record_coverage": sum(1 for item in per_case if item["usage_recorded"]) / len(per_case)
            if per_case else 0.0,
            "avg_cost_usd": _average([item["cost_usd"] for item in per_case if item["cost_usd"] is not None]),
            "avg_latency_ms": _average([item["latency_ms"] for item in per_case if item["latency_ms"] is not None]),
        },
    }


def _validate_case(case: dict[str, Any], index: int) -> None:
    required = {
        "id",
        "category",
        "execution_profile",
        "question",
        "materials",
        "expected_claims",
        "expected_citations",
        "expected_numbers",
    }
    missing = sorted(required - set(case))
    if missing:
        raise ValueError(f"case {index} missing required fields: {', '.join(missing)}")
    if case["category"] not in REQUIRED_CATEGORIES:
        raise ValueError(f"case {case['id']} has unknown category {case['category']!r}")
    if not case["materials"]:
        raise ValueError(f"case {case['id']} must reference at least one material")
    for claim in case["expected_claims"]:
        if claim.get("expected_status") not in {"supported", "contradicted", "insufficient_evidence"}:
            raise ValueError(f"case {case['id']} has invalid claim status")
    if not _case_has_human_label(case):
        raise ValueError(f"case {case['id']} lacks citation or insufficient-evidence labels")


def _case_has_human_label(case: dict[str, Any]) -> bool:
    if case.get("expected_citations"):
        return True
    return any(
        claim.get("expected_status") == "insufficient_evidence"
        for claim in case.get("expected_claims", [])
    )


def _score_case(case: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    expected_evidence = {
        citation["evidence_id"]
        for citation in case.get("expected_citations", [])
        if citation.get("evidence_id")
    }
    retrieved = set(observed.get("retrieved_evidence_ids", []))
    cited = set(observed.get("cited_evidence_ids", []))
    numbers = observed.get("numbers", {})
    usage = observed.get("usage", {})
    return {
        "id": case["id"],
        "observed": bool(observed),
        "retrieval_recall": _recall(retrieved, expected_evidence),
        "retrieval_precision": _precision(retrieved, expected_evidence),
        "citation_precision": _precision(cited, expected_evidence),
        "numerical_consistency": _numerical_score(case.get("expected_numbers", []), numbers),
        "usage_recorded": bool(usage),
        "cost_usd": _optional_float(usage.get("cost_usd") if isinstance(usage, dict) else None),
        "latency_ms": _optional_float(usage.get("latency_ms") if isinstance(usage, dict) else None),
    }


def _recall(observed: set[str], expected: set[str]) -> float | None:
    if not expected:
        return None
    return len(observed & expected) / len(expected)


def _precision(observed: set[str], expected: set[str]) -> float | None:
    if not observed:
        return None
    if not expected:
        return 0.0
    return len(observed & expected) / len(observed)


def _numerical_score(expected_numbers: list[dict[str, Any]], observed: dict[str, Any]) -> float | None:
    if not expected_numbers:
        return None
    matches = 0
    for label in expected_numbers:
        metric = label["metric"]
        expected = float(label["value"])
        tolerance = float(label.get("tolerance", 0.0))
        actual = _optional_float(observed.get(metric))
        if actual is not None and abs(actual - expected) <= tolerance:
            matches += 1
    return matches / len(expected_numbers)


def _average_metric(rows: list[dict[str, Any]], key: str) -> float | None:
    return _average([row[key] for row in rows if row[key] is not None])


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
