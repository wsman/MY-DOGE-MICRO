"""Deterministic claim/evidence support classification."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CitationSupportClassification:
    support_status: str
    confidence: float
    method: str = "deterministic_keyword_number_v1"


class CitationSupportClassifier:
    """Classify evidence support without calling external model APIs."""

    def classify(self, claim_text: str, evidence_snippet: str) -> CitationSupportClassification:
        claim = claim_text.strip()
        evidence = evidence_snippet.strip()
        if not claim or not evidence:
            return CitationSupportClassification("unrelated", 0.0)

        claim_numbers = _numbers(claim)
        evidence_numbers = _numbers(evidence)
        claim_terms = _terms(claim)
        evidence_terms = _terms(evidence)
        overlap = len(claim_terms & evidence_terms)
        overlap_ratio = overlap / len(claim_terms) if claim_terms else 0.0

        if _looks_contradicted(claim, evidence, claim_numbers, evidence_numbers, overlap_ratio):
            return CitationSupportClassification("contradicted", max(0.55, min(0.95, overlap_ratio + 0.35)))

        numbers_match = bool(claim_numbers) and all(
            any(_near(number, ref) for ref in evidence_numbers) for number in claim_numbers
        )
        if numbers_match and overlap_ratio >= 0.25:
            return CitationSupportClassification("supported", min(0.98, 0.65 + overlap_ratio * 0.25))
        if not claim_numbers and overlap_ratio >= 0.55:
            return CitationSupportClassification("supported", min(0.9, 0.55 + overlap_ratio * 0.3))
        if overlap_ratio >= 0.2 or (claim_numbers and bool(evidence_numbers)):
            return CitationSupportClassification("partial", min(0.75, 0.35 + overlap_ratio * 0.4))
        return CitationSupportClassification("unrelated", max(0.1, overlap_ratio))


def _looks_contradicted(
    claim: str,
    evidence: str,
    claim_numbers: list[float],
    evidence_numbers: list[float],
    overlap_ratio: float,
) -> bool:
    claim_lower = claim.lower()
    evidence_lower = evidence.lower()
    if overlap_ratio >= 0.25 and claim_numbers and evidence_numbers:
        return not any(_near(number, ref) for number in claim_numbers for ref in evidence_numbers)
    opposing_pairs = [
        ("increase", "decrease"),
        ("increased", "decreased"),
        ("grew", "declined"),
        ("higher", "lower"),
        ("positive", "negative"),
    ]
    return any(left in claim_lower and right in evidence_lower for left, right in opposing_pairs) or any(
        right in claim_lower and left in evidence_lower for left, right in opposing_pairs
    )


def _terms(text: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", text.lower())
        if len(term) > 2 and not term.isdigit()
    }


def _numbers(text: str) -> list[float]:
    return [float(item) for item in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", text.replace("%", ""))]


def _near(left: float, right: float) -> bool:
    return abs(left - right) <= max(0.01, abs(right) * 0.01)
