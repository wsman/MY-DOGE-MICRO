"""Evidence-aware claim validation for generated reports."""

from __future__ import annotations

import re
from typing import Any

from doge.core.domain.claim_models import ClaimRecord


class ClaimValidationService:
    """Validate extracted claims against retrieved evidence snippets."""

    def validate(
        self,
        *,
        report_id: str,
        claim_text: str,
        evidence_results: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> ClaimRecord:
        if not evidence_results:
            status = "insufficient_evidence"
        elif _claim_matches_evidence(claim_text, evidence_results):
            status = "supported"
        else:
            status = "insufficient_evidence"
        return ClaimRecord.create(
            report_id=report_id,
            text=claim_text,
            status=status,
            evidence_count=len(evidence_results),
            metadata=metadata or {},
        )


def _claim_matches_evidence(claim: str, evidence_results: list[dict[str, Any]]) -> bool:
    numbers = re.findall(r"\d+(?:\.\d+)?", claim)
    texts = " ".join(str(item.get("text") or item.get("support_snippet") or "") for item in evidence_results).lower()
    if numbers:
        return any(number in texts for number in numbers)
    claim_terms = {
        term
        for term in re.findall(r"[\w\u4e00-\u9fff]+", claim.lower())
        if len(term) > 3
    }
    if not claim_terms:
        return False
    evidence_terms = set(re.findall(r"[\w\u4e00-\u9fff]+", texts))
    return bool(claim_terms & evidence_terms)
