"""Repository port for report claims and citations."""

from __future__ import annotations

from typing import Protocol

from doge.core.domain.claim_models import CitationRecord, ClaimEvidenceRelation, ClaimRecord


class IClaimRepository(Protocol):
    """Persist and retrieve material report claims and their citations."""

    def save_claim(self, claim: ClaimRecord) -> None:
        ...

    def list_claims(self, report_id: str) -> list[ClaimRecord]:
        ...

    def save_citation(self, citation: CitationRecord) -> None:
        ...

    def list_citations(
        self,
        *,
        report_id: str | None = None,
        claim_id: str | None = None,
    ) -> list[CitationRecord]:
        ...

    def save_relation(self, relation: ClaimEvidenceRelation) -> None:
        ...

    def list_relations_for_claim(self, claim_id: str) -> list[ClaimEvidenceRelation]:
        ...

    def list_relations_for_evidence(self, evidence_id: str) -> list[ClaimEvidenceRelation]:
        ...
